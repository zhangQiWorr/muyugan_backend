import argparse
import os

import alibabacloud_oss_v2 as oss
import datetime

# 创建一个命令行参数解析器，并描述脚本用途：生成GET方法的预签名URL请求示例
parser = argparse.ArgumentParser(description="presign get object sample")

# 添加命令行参数 --region，表示存储空间所在的区域，必需参数
parser.add_argument('--region', help='The region in which the bucket is located.', required=False)
# 添加命令行参数 --bucket，表示要获取对象的存储空间名称，必需参数
parser.add_argument('--bucket', help='The name of the bucket.', required=False)
# 添加命令行参数 --endpoint，表示其他服务可用来访问OSS的域名，非必需参数
parser.add_argument('--endpoint', help='The domain names that other services can use to access OSS')
# 添加命令行参数 --key，表示对象（文件）在OSS中的键名，必需参数
parser.add_argument('--key', help='The name of the object.', required=False)


def main():
    # 解析命令行提供的参数，获取用户输入的值
    args = parser.parse_args()

    # 从环境变量中加载访问OSS所需的认证信息，用于身份验证
    credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()

    # 使用SDK的默认配置创建配置对象，并设置认证提供者
    cfg = oss.config.load_default()
    cfg.credentials_provider = credentials_provider

    # 设置配置对象的区域属性，根据用户提供的命令行参数
    cfg.region = args.region

    # 如果提供了自定义endpoint，则更新配置对象中的endpoint属性
    if args.endpoint is not None:
        cfg.endpoint = args.endpoint

    # 使用上述配置初始化OSS客户端，准备与OSS交互
    client = oss.Client(cfg)

    print("now time:", datetime.datetime.now())

    # 生成预签名的GET请求
    pre_result = client.presign(
        oss.GetObjectRequest(
            bucket=args.bucket,  # 指定存储空间名称
            key=args.key,  # 指定对象键名
        ),
        expires=datetime.timedelta(hours=1),  # 设置过期时间为1小时
    )

    # 打印预签名请求的方法、过期时间和URL
    print(f'method: {pre_result.method},'
          f' expiration: {pre_result.expiration.strftime("%Y-%m-%dT%H:%M:%S.000Z")},'
          f' url: {pre_result.url}'
          )

    print("now time:", pre_result.expiration.now())

    # 打印预签名请求的已签名头信息
    for key, value in pre_result.signed_headers.items():
        print(f'signed headers key: {key}, signed headers value: {value}')


# 当此脚本被直接执行时，调用main函数开始处理逻辑
if __name__ == "__main__":
    main()  # 脚本入口点，控制程序流程从这里开始