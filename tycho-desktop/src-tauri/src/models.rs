use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemHealth {
    pub engine_status: String,
    pub os_info: String,
    pub app_version: String,
    /// O arquivo M3 existe no caminho controlado pela ponte Marco 5. A busca
    /// ainda valida o contrato promovido antes de devolver resultados.
    pub m4_artifact_available: bool,
    pub m4_artifact_path: String,
    /// Referências históricas opcionais; nunca são copiadas ou usadas pela
    /// rota evidencial Marco 4.
    pub legacy_fase3_available: bool,
    pub legacy_cartography_available: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryResultWrapper {
    pub success: bool,
    pub elapsed_ms: u128,
    pub data_json: String,
    pub error: Option<String>,
}
