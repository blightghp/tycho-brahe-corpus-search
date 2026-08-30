use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemHealth {
    pub engine_status: String,
    pub os_info: String,
    pub app_version: String,
    pub db_exists: bool,
    pub db_path: String,
    pub cartografia_db_exists: bool,
    pub cartografia_db_path: String,
    pub sidecar_binary_exists: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryResultWrapper {
    pub success: bool,
    pub elapsed_ms: u128,
    pub data_json: String,
    pub error: Option<String>,
}
