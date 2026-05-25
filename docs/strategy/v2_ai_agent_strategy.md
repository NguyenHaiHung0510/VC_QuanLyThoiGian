# v2 AI Agent Strategy

## Boi Canh

microSchedule v2 se co AI assistant/agent de doc notes, tasks, calendar va ho tro lap ke hoach. Vi agent co the ghi DB, rui ro sai thao tac cao hon chat/RAG thuong.

## Quyet Dinh

- WS7 lam sau khi UI/data flow v2 on dinh hon.
- Dung LiteLLM cho model/router adapter neu phu hop 9Router.
- Dung LangGraph cho agent multi-step, permission gate va tool state.
- Moi write/admin tool phai co dry-run, confirm, audit log va backup/checkpoint neu rui ro.

## Trade-off

- Lam agent full option C manh hon chat/RAG read-only, nhung phai dau tu safety.
- Khong cho tool bypass service layer: cham hon mot chut, nhung giu consistency va audit.
- Khong hardcode model id cho den khi router `/models` on dinh.

## Tac Dong

- Can `agent_action_log` cho moi confirmed write tool.
- Tool scopes: read-only, propose-only, write-with-confirm, admin.
- Bulk/destructive/admin actions phai tao backup checkpoint truoc.
- UI phai hien proposal va affected ids truoc khi confirm.

## Quality Gates

- Router off khong crash app.
- Secret khong xuat hien trong logs/docs.
- Read tools co citation entity ids.
- Write tools khong mutate neu chua confirm.
- Restore/recovery path ton tai truoc khi bat destructive tool.
