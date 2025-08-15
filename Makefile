# Muyugan 后端系统 Makefile

.PHONY: help install install-dev test test-unit test-integration test-performance test-coverage clean lint format check setup run run-simple run-dev docker-build docker-run docker-stop

# 默认目标
help:
	@echo "Muyugan 后端系统 - 可用命令:"
	@echo ""
	@echo "安装和设置:"
	@echo "  install       安装生产依赖"
	@echo "  install-dev   安装开发依赖"
	@echo "  setup         设置开发环境"
	@echo ""
	@echo "测试:"
	@echo "  test          运行所有测试"
	@echo "  test-unit     运行单元测试"
	@echo "  test-integration 运行集成测试"
	@echo "  test-performance 运行性能测试"
	@echo "  test-coverage 运行测试并生成覆盖率报告"
	@echo ""
	@echo "代码质量:"
	@echo "  lint          运行代码检查"
	@echo "  format        格式化代码"
	@echo "  check         运行所有代码质量检查"
	@echo ""
	@echo "运行:"
	@echo "  run           运行完整版本 (main.py)"
	@echo "  run-simple    运行简化版本 (main_simple.py)"
	@echo "  run-dev       运行开发版本 (带重载)"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build  构建Docker镜像"
	@echo "  docker-run    运行Docker容器"
	@echo "  docker-stop   停止Docker容器"
	@echo ""
	@echo "维护:"
	@echo "  clean         清理临时文件"
	@echo "  logs          查看日志文件"

# 安装依赖
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

# 设置开发环境
setup: install-dev
	@echo "设置开发环境..."
	python -m pip install --upgrade pip
	pre-commit install
	@echo "开发环境设置完成!"

# 测试命令
test:
	python run_tests.py --type all

test-unit:
	python run_tests.py --type unit

test-integration:
	python run_tests.py --type integration

test-performance:
	python run_tests.py --type performance

test-coverage:
	python run_tests.py --coverage

# 代码质量检查
lint:
	@echo "运行代码检查..."
	flake8 muyugan_backend/
	mypy muyugan_backend/
	bandit -r muyugan_backend/
	@echo "代码检查完成!"

format:
	@echo "格式化代码..."
	black muyugan_backend/
	isort muyugan_backend/
	@echo "代码格式化完成!"

check: format lint test
	@echo "所有检查完成!"

# 运行应用
run: ## 运行完整应用（AI聊天 + 知识付费）
	@echo "🚀 启动AI智能聊天 + 知识付费App后端系统..."
	@echo "系统将自动检测依赖并选择运行模式"
	python3 main.py

run-dev: ## 开发模式运行（自动重载）
	@echo "🔧 开发模式启动..."
	@echo "系统将自动检测依赖并选择运行模式"
	python3 main.py

# Docker命令
docker-build:
	@echo "构建Docker镜像..."
	docker build -t muyugan-backend .

docker-run:
	@echo "运行Docker容器..."
	docker run -d --name muyugan-backend -p 8000:8000 muyugan-backend

docker-stop:
	@echo "停止Docker容器..."
	docker stop muyugan-backend
	docker rm muyugan-backend

# 维护命令
clean:
	@echo "清理临时文件..."
	python run_tests.py --clean
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type f -name "test.db" -delete
	@echo "清理完成!"

logs:
	@echo "查看日志文件..."
	@if [ -d "logs" ]; then \
		echo "应用日志:"; \
		tail -f logs/muyugan_app.log; \
	else \
		echo "日志目录不存在"; \
	fi

# 数据库命令
db-migrate:
	@echo "运行数据库迁移..."
	python database/migrate_knowledge_app.py

db-reset:
	@echo "重置数据库..."
	@echo "警告: 这将删除所有数据!"
	@read -p "确认继续? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		python database/migrate_knowledge_app.py --reset; \
	else \
		echo "操作已取消"; \
	fi

# 性能测试
benchmark:
	@echo "运行性能基准测试..."
	python -m pytest tests/test_performance.py -v --benchmark-only

# 安全检查
security-check:
	@echo "运行安全检查..."
	bandit -r muyugan_backend/ -f json -o security-report.json
	safety check
	@echo "安全检查完成!"

# 文档生成
docs:
	@echo "生成文档..."
	cd docs && make html
	@echo "文档已生成到 docs/_build/html/"

# 部署准备
deploy-prep:
	@echo "准备部署..."
	python -m pytest --cov=muyugan_backend --cov-report=xml
	@echo "部署准备完成!"

# 开发工作流
dev-workflow: format lint test
	@echo "开发工作流完成!"

# 快速测试
quick-test:
	@echo "运行快速测试..."
	python -m pytest tests/ -x --tb=short --maxfail=3

# 监控
monitor:
	@echo "启动监控..."
	@echo "按 Ctrl+C 停止监控"
	watch -n 1 'ps aux | grep python | grep -v grep'
