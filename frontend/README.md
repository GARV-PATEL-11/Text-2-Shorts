# frontend/

Reserved for a user interface (for example a web page to review scene previews and approve checkpoints). There is
no frontend code yet: today the user works through the `text-2-shorts` command and the Claude Code session
(`runtime-environment/`). A frontend would talk to the backend only through the `text-2-shorts` commands and the
run's files, whose contracts are the Pydantic models in `backend/schemas/`.
