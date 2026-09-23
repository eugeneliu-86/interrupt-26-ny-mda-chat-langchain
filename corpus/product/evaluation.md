# Evaluation

Build an offline evaluation in three steps:

1. Create a dataset in LangSmith (UI or `client.create_dataset`).
2. Write an evaluator function (LLM-as-judge or pure-code) returning
   `{"key": "...", "score": 0.0 or 1.0}`.
3. Run `from langsmith import evaluate; evaluate(target_fn, data=DATASET, evaluators=[...])`.

For online evaluation, register a run rule in the LangSmith Evaluators UI.
Every new trace in the project will be scored automatically.
