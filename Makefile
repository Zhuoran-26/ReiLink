.PHONY: install-backend install-desktop dev-backend dev-desktop test test-backend test-desktop test-e2e lint typecheck

install-backend:
	cd services/backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

install-desktop:
	cd apps/desktop && npm install

dev-backend:
	cd services/backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

dev-desktop:
	cd apps/desktop && npm run dev

test: test-backend test-desktop

test-backend:
	services/backend/.venv/bin/python -m pytest services/backend/tests

test-desktop:
	cd apps/desktop && npm test

test-e2e:
	cd apps/desktop && npm run test:e2e

lint:
	cd apps/desktop && npm run lint

typecheck:
	cd apps/desktop && npm run build
