# Environment

Recommended environment variables for a typical LangChain + LangSmith app:

```bash
ANTHROPIC_API_KEY=sk-ant-...          # or OPENAI_API_KEY, etc.
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_TRACING=true                # enables tracing on every run
LANGSMITH_PROJECT=my-project          # auto-created on first trace
```

Load with python-dotenv at the top of your entrypoint:
```python
from dotenv import load_dotenv
load_dotenv(override=True)
```
