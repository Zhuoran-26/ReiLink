.PHONY: install-backend install-desktop dev-backend dev-desktop dev dev-renderer doctor validate-knowledge package-desktop test test-backend test-desktop test-e2e lint typecheck

PYTHON ?= python3

install-backend:
	cd services/backend && $(PYTHON) -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

install-desktop:
	cd apps/desktop && npm install

dev-backend:
	cd services/backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

dev-desktop:
	cd apps/desktop && npm run dev:electron

dev:
	@echo "ReiLink dev 需要两个长期进程，请分别打开两个终端："
	@echo "  终端 A: make dev-backend"
	@echo "  终端 B: make dev-desktop"
	@echo "启动前建议先运行: make doctor"

doctor:
	@$(PYTHON) scripts/doctor.py
	@echo "可选知识包检查: make validate-knowledge"

validate-knowledge:
	@$(PYTHON) scripts/validate_knowledge.py

package-desktop:
	cd apps/desktop && npm run package

dev-renderer:
	cd apps/desktop && npm run dev

test: test-backend test-desktop

test-backend:
	PYTHONPATH=.:services/backend LLM_PROVIDER=mock DEEPSEEK_API_KEY= services/backend/.venv/bin/python -m pytest services/backend/tests

test-desktop:
	cd apps/desktop && npm test

test-e2e:
	cd apps/desktop && npm run test:e2e

lint:
	cd apps/desktop && npm run lint
	git diff --check

typecheck:
	cd apps/desktop && npm run build
