from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings


def llm_is_configured() -> bool:
    if settings.llm_provider == "gemini":
        return bool(settings.google_api_key)
    if settings.llm_provider == "azure_openai":
        return bool(
            settings.azure_openai_api_key
            and settings.azure_openai_endpoint
            and settings.azure_openai_deployment
        )
    return False


def missing_llm_config_message() -> str:
    if settings.llm_provider == "gemini":
        return "AI responses require GOOGLE_API_KEY (Gemini)."
    if settings.llm_provider == "azure_openai":
        return (
            "AI responses require AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, "
            "and AZURE_OPENAI_DEPLOYMENT."
        )
    return f"Unknown LLM_PROVIDER: {settings.llm_provider}"


def build_chat_model() -> BaseChatModel:
    if settings.llm_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_tokens,
        )

    if settings.llm_provider == "azure_openai":
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_openai_deployment,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
