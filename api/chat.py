"""
聊天相关API
包含普通聊天、流式聊天和WebSocket聊天功能
"""

import os
import json
import uuid
import asyncio
from typing import Dict, List, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages.ai import  AIMessageChunk
from langchain_core.messages.tool import ToolMessage

from models import get_db
from models.user import User
from models.conversation import Conversation, Message
from models.schemas import StreamChatRequest
from api.auth import get_current_user
from services.logger import get_logger

logger = get_logger("chat_api")
chat_logger = get_logger("chat")
router = APIRouter(prefix="/chat", tags=["聊天"])

# 存储每个请求的中断标志
stop_events = {}  # {request_id: asyncio.Event}


def get_agent_manager():
    """获取智能体管理器"""
    from main import app
    return app.state.agent_manager


def build_multimodal_message(text: str, images: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    构建多模态消息
    
    Args:
        text: 文本内容
        images: 图片列表，每个图片包含url等信息
    
    Returns:
        多模态消息字典
    """
    content = []
    
    # 添加图片内容
    for image_att in images:
        image_url = image_att.get("url", "")
        
        # 判断是否为本地路径
        if is_local_path(image_url):
            # 本地路径，转换为base64
            try:
                base64_image = convert_local_image_to_base64(image_url)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": base64_image}
                })
                chat_logger.info(f"🖼️ 本地图片已转换为base64: {image_url}")
            except Exception as e:
                chat_logger.error(f"❌ 本地图片转换base64失败: {image_url}, 错误: {str(e)}")
                # 转换失败时使用原始URL
                content.append({
                    "type": "image_url",
                    "image_url": {"url": image_url}
                })
        else:
            # 网络URL或其他格式，直接使用
            content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })
            chat_logger.info(f"🖼️ 使用图片URL: {image_url}")
    
    # 添加文本内容
    content.append({
        "type": "text",
        "text": text
    })
    
    return {
        "role": "user",
        "content": content
    }


def is_local_path(url: str) -> bool:
    """
    判断是否为本地路径
    
    Args:
        url: 图片URL或路径
        
    Returns:
        是否为本地路径
    """
    # 检查是否为网络URL
    if url.startswith(('http://', 'https://', 'ftp://', 'sftp://')):
        return False
    
    # 检查是否为相对路径（以/static/开头）
    if url.startswith('/static/'):
        return True
    
    # 检查是否为绝对路径
    if os.path.isabs(url):
        return True
    
    # 检查是否为相对路径（不以http等开头）
    if not url.startswith(('http', 'ftp', 'sftp')):
        return True
    
    return False


def convert_local_image_to_base64(image_path: str) -> str:
    """
    将本地图片转换为base64编码
    
    Args:
        image_path: 本地图片路径
        
    Returns:
        base64编码的图片字符串
    """
    import base64
    from PIL import Image

    # 如果是相对路径，转换为绝对路径
    if image_path.startswith('/static/'):
        # 从/static/路径转换为实际文件路径
        base_dir = os.path.dirname(os.path.dirname(__file__))
        image_path = os.path.join(base_dir, image_path.lstrip('/'))
    
    # 检查文件是否存在
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片文件不存在: {image_path}")
    
    # 检查文件是否为图片
    try:
        with Image.open(image_path) as img:
            # 获取图片格式
            format_name = img.format.lower()
            
            # 重新读取图片并转换为base64
            with open(image_path, 'rb') as f:
                image_data = f.read()
                
            # 根据图片格式确定MIME类型
            mime_type_map = {
                'jpeg': 'image/jpeg',
                'jpg': 'image/jpeg',
                'png': 'image/png',
                'gif': 'image/gif',
                'webp': 'image/webp',
                'bmp': 'image/bmp'
            }
            
            mime_type = mime_type_map.get(format_name, 'image/jpeg')


            
            # 转换为base64
            base64_data = base64.b64encode(image_data).decode('utf-8')
            base64_url = f"data:{mime_type};base64,{base64_data}"
            
            chat_logger.info(f"🔄 图片转换成功: {image_path} -> {mime_type}")
            return base64_url
            
    except Exception as e:
        raise Exception(f"图片转换失败: {str(e)}")


def save_partial_ai_response(conversation_id: str, partial_response: str, total_tokens: int, 
                              tool_calls_data: List[Dict], tools_results: List[Dict], is_interrupted: bool = True):
    """
    保存部分AI回复和工具调用信息到数据库（用于流式对话中断）
    
    Args:
        conversation_id: 对话ID
        partial_response: 部分AI回复内容
        total_tokens: 消耗的token数
        tool_calls_data: 工具调用信息列表
        tools_results: 工具执行结果列表
        is_interrupted: 是否为中断状态
    """
    try:
        from models import SessionLocal
        with SessionLocal() as save_db:
            # 1. 保存部分AI消息
            ai_message = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=partial_response,
                token_count=total_tokens,
                tool_calls=tool_calls_data,  # 保存工具调用信息
                message_metadata={
                    "tools_used": len(tool_calls_data),
                    "tools_results": tools_results,
                    "processing_time": datetime.utcnow().isoformat(),
                    "is_interrupted": is_interrupted,  # 标记为中断状态
                    "interrupt_reason": "user_stopped" if is_interrupted else "completed"
                }
            )
            save_db.add(ai_message)

            # 2. 如果有工具调用，单独保存工具调用消息
            for i, (tool_call, tool_result) in enumerate(zip(tool_calls_data, tools_results)):
                tool_message = Message(
                    conversation_id=conversation_id,
                    role="tool",
                    content=json.dumps(tool_result, ensure_ascii=False),
                    tool_call_id=tool_call.get("id"),
                    message_metadata={
                        "tool_name": tool_call.get("name"),
                        "tool_args": tool_call.get("args"),
                        "execution_status": tool_result.get("status", "success"),
                        "execution_time": tool_result.get("execution_time"),
                        "error_message": tool_result.get("error") if tool_result.get("status") == "error" else None,
                        "is_interrupted": is_interrupted
                    }
                )
                save_db.add(tool_message)

            # 3. 更新对话统计
            conversation_to_update = save_db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            if conversation_to_update:
                conversation_to_update.message_count += 2  # user + assistant
                conversation_to_update.last_message_at = datetime.utcnow()
                conversation_to_update.total_tokens += total_tokens
            
            save_db.commit()
            
            status_msg = "中断" if is_interrupted else "完成"
            chat_logger.info(f"💾 {status_msg}状态下的AI回复和{len(tool_calls_data)}个工具调用已保存到数据库")
            
    except Exception as save_error:
        chat_logger.error(f"❌ 保存部分AI回复和工具调用失败: {save_error}")
        import traceback
        chat_logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")


# @router.post("", response_model=dict)
# async def chat(
#     chat_request: ChatRequest,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """发送聊天消息"""
#
#     # 获取智能体管理器
#     agent_manager = get_agent_manager()
#     agent_id = chat_request.agent_id
#     try:
#         # 获取或创建对话
#         conversation = None
#         if chat_request.conversation_id:
#             conversation = db.query(Conversation).filter(
#                 Conversation.id == chat_request.conversation_id,
#                 Conversation.user_id == current_user.id,
#                 Conversation.is_deleted == False
#             ).first()
#
#             if not conversation:
#                 raise HTTPException(
#                     status_code=status.HTTP_404_NOT_FOUND,
#                     detail="对话不存在"
#                 )
#         else:
#             # 创建新对话
#             try:
#                 agent = await agent_manager.get_agent_by_id(db, agent_id)
#
#                 conversation = Conversation(
#                     user_id=current_user.id,
#                     agent_id=agent.id,
#                     title=f"与{agent.display_name}的对话"
#                 )
#                 db.add(conversation)
#                 db.commit()
#                 db.refresh(conversation)
#             except Exception as e:
#                 chat_logger.error(f"❌ 创建对话失败: {str(e)}")
#                 raise
#
#         # 处理附件信息
#         attachments_info = None
#         if chat_request.attachments:
#             # 检查是否包含图片附件
#             image_attachments = [att for att in chat_request.attachments if att.get("type") == "image"]
#             if image_attachments:
#                 attachments_info = {
#                     "has_images": True,
#                     "image_count": len(image_attachments),
#                     "images": image_attachments
#                 }
#                 chat_logger.info(f"🖼️ 检测到 {len(image_attachments)} 张图片附件")
#             else:
#                 attachments_info = {
#                     "has_images": False,
#                     "attachments": chat_request.attachments
#                 }
#                 chat_logger.info(f"📎 检测到 {len(chat_request.attachments)} 个非图片附件")
#
#         # 保存用户消息
#         try:
#             user_message = Message(
#                 conversation_id=conversation.id,
#                 role="user",
#                 content=chat_request.message,
#                 message_metadata=attachments_info if attachments_info else None
#             )
#             db.add(user_message)
#             db.commit()
#         except Exception as e:
#             chat_logger.error(f"❌ 保存用户消息失败: {str(e)}")
#             raise
#
#         # 获取智能体实例
#         try:
#             with PostgresSaver.from_conn_string(os.getenv("DATABASE_URL")) as checkpointer:
#                 agent_instance = await agent_manager.get_agent_instance(
#                     db, agent_id, checkpointer
#                 )
#
#                 # 调用智能体处理消息
#                 config = {
#                     "configurable": {
#                         "thread_id": conversation.id,
#                         "user_id": current_user.id,
#                         "user_name": current_user.username
#                     }
#                 }
#                 # 构建消息历史，支持多模态输入
#                 if attachments_info and attachments_info.get("has_images"):
#                     # 如果有图片附件，构建多模态消息
#                     user_message = build_multimodal_message(
#                         chat_request.message,
#                         attachments_info.get("images", [])
#                     )
#                     messages = [user_message]
#                     chat_logger.info(f"🖼️ 构建多模态消息，包含 {len(attachments_info.get('images', []))} 张图片")
#                 else:
#                     # 普通文本消息
#                     messages = [{"role": "user", "content": chat_request.message}]
#                     chat_logger.info(f"📋 构建普通文本消息")
#
#                 chat_logger.info(f"📋 构建消息历史: {messages}")
#
#                 # 调用智能体
#                 response = agent_instance.invoke(
#                     {"messages": messages},
#                     config=config
#                 )
#
#                 chat_logger.info(f"📋 响应内容结构: {response}")
#
#                 # 获取AI回复和工具调用信息
#                 if "messages" in response and len(response["messages"]) > 0:
#                     ai_response = response["messages"][-1].content
#                 else:
#                     chat_logger.error(f"❌ AI响应格式异常: {response}")
#                     raise Exception("AI响应格式异常，未找到messages字段")
#
#                 # 保存AI回复
#                 ai_message = Message(
#                     conversation_id=conversation.id,
#                     role="assistant",
#                     content=ai_response
#                 )
#                 db.add(ai_message)
#
#                 # 更新对话统计
#                 conversation.message_count += 2
#                 conversation.last_message_at = datetime.utcnow()
#
#                 db.commit()
#                 result = {
#                     "conversation_id": conversation.id,
#                     "response": ai_response,
#                     "timestamp": datetime.utcnow().isoformat()
#                 }
#                 chat_logger.info(f"🎉 聊天处理完成，返回结果")
#                 return result
#
#         except Exception as e:
#             chat_logger.error(f"❌ 智能体实例化处理失败: {str(e)}")
#             import traceback
#             chat_logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
#             db.rollback()
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail=f"智能体实例化处理失败: {str(e)}"
#             )
#
#     except HTTPException:
#         # 重新抛出HTTP异常
#         raise
#     except Exception as e:
#         chat_logger.error(f"❌ 聊天接口未预期错误: {str(e)}")
#         chat_logger.error(f"❌ 错误类型: {type(e)}")
#         import traceback
#         chat_logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
#
#         # 确保数据库回滚
#         try:
#             db.rollback()
#         except Exception as rollback_error:
#             chat_logger.error(f"❌ 数据库回滚失败: {str(rollback_error)}")
#
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"聊天处理失败: {str(e)}"
#         )


@router.post("/stream")
async def stream_chat(
    chat_request: StreamChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """流式聊天接口"""
    try:

        request_id = str(uuid.uuid4())
        stop_event = asyncio.Event()
        stop_events[request_id] = stop_event
        
        # 获取智能体管理器
        agent_manager = get_agent_manager()
        agent_id = chat_request.agent_id
        chat_logger.info(f"🚀 流式聊天请求: {chat_request.message[:50]}...")
        
        # 提前提取用户信息，避免在异步生成器中访问detached对象
        user_id = current_user.id
        user_name = current_user.username
        # 获取或创建对话
        conversation = None
        agent = await agent_manager.get_agent_by_id(db, agent_id)
        if chat_request.conversation_id:
            conversation = db.query(Conversation).filter(
                    Conversation.id == chat_request.conversation_id,
                    Conversation.user_id == user_id,
                    Conversation.is_deleted == False
            ).first()
            
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="对话不存在"
                )
        else:
            # 创建新对话
            try:
                conversation = Conversation(
                    user_id = user_id,
                    agent_id = agent.id,
                    title = f"与{agent.display_name}的对话"
                )
                db.add(conversation)
                db.commit()
                db.refresh(conversation)
            except Exception as e:
                chat_logger.error(f"❌ 创建对话失败: {str(e)}")
                raise

        # 处理附件信息
        attachments_info = None
        model_name = ""
        base_url = ""
        api_key_name = ""
        if chat_request.attachments:
            # 检查是否包含图片附件
            image_attachments = [att for att in chat_request.attachments if att.get("type") == "image"]
            if image_attachments:
                attachments_info = {
                    "has_images": True,
                    "image_count": len(image_attachments),
                    "images": image_attachments
                }
                chat_logger.info(f"🖼️ 检测到 {len(image_attachments)} 张图片附件")
            else:
                attachments_info = {
                    "has_images": False,
                    "attachments": chat_request.attachments
                }
                chat_logger.info(f"📎 检测到 {len(chat_request.attachments)} 个非图片附件")
        
        # 保存用户消息
        try:
            user_message = Message(
                conversation_id=conversation.id,
                role="user",
                content=chat_request.message,
                message_metadata=attachments_info if attachments_info else None
            )
            db.add(user_message)
            db.commit()
        except Exception as e:
            chat_logger.error(f"❌ 保存用户消息失败: {str(e)}")
            raise

        # 提取对话ID，避免在异步生成器中访问detached对象
        conversation_id = conversation.id

        # 生成流式响应
        async def generate_stream():
            # 初始化变量
            full_response = ""
            total_tokens = 0
            tool_calls_data = []  # 工具调用信息
            tools_results = []    # 工具执行结果
            current_tool_call = None  # 当前工具调用
            model_name = ""
            base_url = ""
            api_key_name = ""
            # 构建消息历史，支持多模态输入
            messages = []
            # 添加当前用户消息

            if attachments_info and attachments_info.get("has_images"):
                model_name = os.getenv("VISION_MODEL_NAME")
                base_url = os.getenv("VISION_MODEL_BASE_URL")
                api_key_name = os.getenv("VISION_MODEL_API_KEY_NAME")
                chat_logger.info(f"model_name:{model_name}")
                chat_logger.info(f"base_url:{base_url}")
                # 如果有图片附件，构建多模态消息
                current_user_message = build_multimodal_message(
                    chat_request.message,
                    attachments_info.get("images", [])
                )
                messages.append(current_user_message)
                chat_logger.info(f"🖼️ 构建多模态消息，包含 {len(attachments_info.get('images', []))} 张图片")
            else:
                # 普通文本消息
                messages.append({
                    "role": "user",
                    "content": chat_request.message
                })
                chat_logger.info(f"📋 构建普通文本消息")
            try:
                # 发送初始响应
                with PostgresSaver.from_conn_string(os.getenv("DATABASE_URL")) as checkpointer:
                    # 获取智能体实例
                    agent_instance = await agent_manager.get_agent_instance(
                        db,agent_id, model_name, base_url, api_key_name, checkpointer
                    )

                    # 调用智能体处理消息
                    config = {
                        "configurable": {
                            "thread_id": conversation_id,
                            "user_id": user_id,
                            "user_name": user_name
                        }
                    }
                    # 使用流式调用智能体 - 完整工具调用处理
                    yield f"data: {json.dumps({'type': 'start', 'conversation_id': conversation_id, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                    for chunk in agent_instance.stream(
                            {"messages": messages},
                            config=config,
                            stream_mode="messages"
                        ):
                        message = chunk[0] if chunk else None
                        if not message:
                            continue
                            
                        # 处理AI文本响应
                        if isinstance(message, AIMessageChunk):
                            # 文本内容
                            if message.content:
                                chat_logger.info(f"🎉 获取到AI回复: {message.content}")
                                full_response += message.content
                                yield f"data: {json.dumps({'type': 'token', 'content': message.content})}\n\n"

                            # Token使用情况
                            if hasattr(message, 'usage_metadata') and message.usage_metadata:
                                total_tokens += message.usage_metadata.get("total_tokens", 0)
                                chat_logger.info(f"🧮 消耗token数: {total_tokens}")

                            # 工具调用信息（AI消息中的工具调用）
                            if hasattr(message, 'tool_calls') and message.tool_calls:
                                for tool in message.tool_calls:
                                    if tool.get("name"):
                                        tool_call_info = {
                                            "id":tool.get("id"),
                                            "name": tool.get("name"),
                                            "args": tool.get("args")
                                        }
                                        tool_calls_data.append(tool_call_info)
                                        current_tool_call = tool_call_info

                                        # 发送工具调用开始信号
                                        yield f"data: {json.dumps({'type': 'tool_call_start', 'tool': tool_call_info})}\n\n"
                                        chat_logger.info(f"🛠️ 开始工具调用: {tool.get("name")} - 参数: {tool.get("args")}")


                        # 处理工具执行结果
                        elif isinstance(message, ToolMessage):
                            tool_result = {
                                "tool_call_id": getattr(message, 'tool_call_id', ''),
                                "name": getattr(message, 'name', ''),
                                "content": message.content,
                                "status": "success",
                                "execution_time": datetime.utcnow().isoformat()
                            }
                            
                            # 检查是否有错误
                            if hasattr(message, 'status') and message.status == 'error':
                                tool_result["status"] = "error"
                                tool_result["error"] = message.content
                            
                            tools_results.append(tool_result)
                            
                            # 发送工具执行结果
                            yield f"data: {json.dumps({'type': 'tool_result', 'result': tool_result})}\n\n"
                            chat_logger.info(f"🔧 工具执行完成: {tool_result['content']} - 状态: {tool_result['status']}")

                    # 正常完成时保存完整的AI回复和工具调用信息
                    save_partial_ai_response(conversation_id, full_response, total_tokens,
                                             tool_calls_data, tools_results, is_interrupted=False)

                    # 发送结束信号，包含工具调用统计
                    end_data = {
                        'type': 'end', 
                        'response': full_response, 
                        'timestamp': datetime.utcnow().isoformat(),
                        'tools_used': len(tool_calls_data),
                        'total_tokens': total_tokens
                    }
                    yield f"data: {json.dumps(end_data)}\n\n"

                    chat_logger.info(f"🎉 流式聊天处理完成")

            except (asyncio.CancelledError, GeneratorExit) as e:
                # 处理用户中断流式对话的情况
                chat_logger.info(f"⚠️ 用户中断流式对话: {type(e).__name__}")
                
                # 保存部分生成的消息
                if full_response or tool_calls_data:
                    save_partial_ai_response(
                        conversation_id=conversation_id,
                        partial_response=full_response,
                        total_tokens=total_tokens,
                        tool_calls_data=tool_calls_data,
                        tools_results=tools_results,
                        is_interrupted=True
                    )

                    # stop_event.set()
                    # # 发送中断信号
                    # try:
                    #     interrupt_data = {
                    #         'type': 'interrupted',
                    #         'partial_response': full_response,
                    #         'timestamp': datetime.utcnow().isoformat(),
                    #         'tools_used': len(tool_calls_data),
                    #         'total_tokens': total_tokens,
                    #         'reason': 'user_stopped'
                    #     }
                    #     yield f"data: {json.dumps(interrupt_data)}\n\n"
                    # except:
                    #     # 如果连接已断开，忽略发送错误
                    #     chat_logger.warning(f"⚠️ 连接已断开，忽略发送错误")
                    #     pass
                
                # 重新抛出异常以确保正确的清理
                raise
                
            except Exception as e:
                chat_logger.error(f"❌ 流式聊天处理失败: {str(e)}")
                import traceback
                chat_logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
                
                # 即使出错也要尝试保存部分消息
                if full_response or tool_calls_data:
                    save_partial_ai_response(
                        conversation_id=conversation_id,
                        partial_response=full_response,
                        total_tokens=total_tokens,
                        tool_calls_data=tool_calls_data,
                        tools_results=tools_results,
                        is_interrupted=True
                    )
                
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                
            finally:
                # 确保资源清理
                chat_logger.info(f"🧹 流式对话资源清理完成")

        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
            
    except HTTPException:
        raise
    except Exception as e:
        chat_logger.error(f"❌ 流式聊天接口未预期错误: {str(e)}")
        import traceback
        chat_logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"流式聊天处理失败: {str(e)}"
        )


# WebSocket聊天接口
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_message(self, message: str, session_id: str):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_text(message)

manager = ConnectionManager()

@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """WebSocket聊天端点"""
    await manager.connect(websocket, conversation_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # 这里可以处理WebSocket消息
            # 实现实时聊天功能
            
            await manager.send_message(
                json.dumps({"type": "response", "message": "消息已收到"}),
                conversation_id
            )
            
    except WebSocketDisconnect:
        manager.disconnect(conversation_id) 