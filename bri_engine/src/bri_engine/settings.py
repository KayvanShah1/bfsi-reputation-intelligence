from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_root: Path = Field(default_factory=Path.cwd, validation_alias="BRI_PROJECT_ROOT")
    raw_data_dir: Path = Field(Path("data/raw"), validation_alias="BRI_RAW_DATA_DIR")
    processed_data_dir: Path = Field(
        Path("data/processed"),
        validation_alias="BRI_PROCESSED_DATA_DIR",
    )
    taxonomy_path: Path = Field(Path("config/taxonomy.yml"), validation_alias="BRI_TAXONOMY_PATH")
    source_mapping_path: Path = Field(
        Path("config/source_mapping.yml"),
        validation_alias="BRI_SOURCE_MAPPING_PATH",
    )
    raw_dataset_name: str = Field("Dataset.xlsx", validation_alias="BRI_RAW_DATASET_NAME")
    reference_input_path: Path = Field(
        Path("docs/references/Dataset.xlsx"),
        validation_alias="BRI_REFERENCE_INPUT_PATH",
    )
    input_path_override: Path | None = Field(default=None, validation_alias="BRI_INPUT_PATH")
    output_stem: str = Field("classified_mentions", validation_alias="BRI_OUTPUT_STEM")
    llm_cache_name: str = Field("llm_cache.json", validation_alias="BRI_LLM_CACHE_NAME")
    summary_name: str = Field("pipeline_summary.json", validation_alias="BRI_SUMMARY_NAME")

    openrouter_enabled: bool = Field(
        False,
        validation_alias=AliasChoices("OPENROUTER_ENABLED", "BRI_OPENROUTER_ENABLED"),
    )
    openrouter_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "BRI_OPENROUTER_API_KEY"),
    )
    openrouter_base_url: str = Field(
        "https://openrouter.ai/api/v1",
        validation_alias=AliasChoices("OPENROUTER_BASE_URL", "BRI_OPENROUTER_BASE_URL"),
    )
    openrouter_model: str = Field(
        "openrouter/free",
        validation_alias=AliasChoices("OPENROUTER_MODEL", "BRI_OPENROUTER_MODEL"),
    )
    openrouter_timeout_seconds: float = Field(
        30.0,
        validation_alias=AliasChoices(
            "OPENROUTER_TIMEOUT_SECONDS",
            "BRI_OPENROUTER_TIMEOUT_SECONDS",
        ),
    )
    openrouter_temperature: float = Field(
        0.0,
        validation_alias=AliasChoices("OPENROUTER_TEMPERATURE", "BRI_OPENROUTER_TEMPERATURE"),
    )
    openrouter_max_tokens: int = Field(
        500,
        validation_alias=AliasChoices("OPENROUTER_MAX_TOKENS", "BRI_OPENROUTER_MAX_TOKENS"),
    )
    openrouter_retries: int = Field(
        1,
        validation_alias=AliasChoices("OPENROUTER_RETRIES", "BRI_OPENROUTER_RETRIES"),
    )

    def resolve_path(self, path: Path) -> Path:
        return path if path.is_absolute() else self.project_root / path

    @property
    def raw_input_path(self) -> Path:
        return self.resolve_path(self.raw_data_dir) / self.raw_dataset_name

    @property
    def input_path(self) -> Path:
        if self.input_path_override is not None:
            return self.resolve_path(self.input_path_override)
        raw_path = self.raw_input_path
        if raw_path.exists():
            return raw_path
        return self.resolve_path(self.reference_input_path)

    @property
    def output_csv_path(self) -> Path:
        return self.resolve_path(self.processed_data_dir) / f"{self.output_stem}.csv"

    @property
    def output_xlsx_path(self) -> Path:
        return self.resolve_path(self.processed_data_dir) / f"{self.output_stem}.xlsx"

    @property
    def output_parquet_path(self) -> Path:
        return self.resolve_path(self.processed_data_dir) / f"{self.output_stem}.parquet"

    @property
    def summary_path(self) -> Path:
        return self.resolve_path(self.processed_data_dir) / self.summary_name

    @property
    def llm_cache_path(self) -> Path:
        return self.resolve_path(self.processed_data_dir) / self.llm_cache_name

    @property
    def resolved_taxonomy_path(self) -> Path:
        return self.resolve_path(self.taxonomy_path)

    @property
    def resolved_source_mapping_path(self) -> Path:
        return self.resolve_path(self.source_mapping_path)

    @property
    def openrouter_api_key_value(self) -> str | None:
        if self.openrouter_api_key is None:
            return None
        return self.openrouter_api_key.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()
