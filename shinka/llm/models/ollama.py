from typing import Any, Dict, List
from .result import QueryResult


def query_ollama(
    client: Any,
    model_name: str,
    msg: str,
    system_msg: str,
    msg_history: List[Dict],
    output_model=None,
    model_posteriors=None,
    **kwargs,
) -> QueryResult:
    if output_model is not None:
        raise ValueError("Structured outputs are not supported for Ollama models.")

    new_msg_history = msg_history + [{"role": "user", "content": msg}]

    options = dict(kwargs.get("options", {}))
    if "temperature" in kwargs:
        options.setdefault("temperature", kwargs["temperature"])
    if "top_p" in kwargs:
        options.setdefault("top_p", kwargs["top_p"])
    if "top_k" in kwargs:
        options.setdefault("top_k", int(kwargs["top_k"]))
    max_tokens = kwargs.get("max_tokens") or kwargs.get("max_output_tokens")
    if max_tokens is not None:
        options.setdefault("num_predict", int(max_tokens))

    response = client.chat(
        model=model_name[8:],  # remove "ollama::" prefix
        messages=_build_messages(system_msg, msg_history, msg),
        options=options or None,
    )
    message = response.get("message", {}) or {}
    content = message.get("content", "")
    new_msg_history.append({"role": "assistant", "content": content})

    metrics = response.get("metrics", {}) or {}
    input_tokens = int(metrics.get("prompt_tokens") or 0)
    output_tokens = int(metrics.get("completion_tokens") or 0)

    return QueryResult(
        content=content,
        msg=msg,
        system_msg=system_msg,
        new_msg_history=new_msg_history,
        model_name=model_name,
        kwargs=kwargs,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=0.0,
        input_cost=0.0,
        output_cost=0.0,
        thought="",
        model_posteriors=model_posteriors,
    )


def _build_messages(system_msg: str, msg_history: List[Dict], msg: str) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    if system_msg:
        messages.append({"role": "system", "content": system_msg})
    if msg_history:
        messages.extend(msg_history)
    messages.append({"role": "user", "content": msg})
    return messages
