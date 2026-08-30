use std::path::PathBuf;
use std::time::Instant;
use tauri::{AppHandle, Manager};
use tauri_plugin_shell::ShellExt;
use crate::models::{QueryResultWrapper, SystemHealth};

#[tauri::command]
pub async fn check_system_health(app: AppHandle) -> Result<SystemHealth, String> {
    let app_data_dir = app.path().app_data_dir().unwrap_or_else(|_| PathBuf::from("."));
    let db_path = app_data_dir.join("corpus_fase3.db");
    let cartografia_db_path = app_data_dir.join("corpus_cartografia.db");

    let local_db = PathBuf::from("corpus_fase3.db");
    let local_cart = PathBuf::from("corpus_cartografia.db");
    let corpus_data_db = PathBuf::from("../../corpus_data/corpus_fase3.db");
    let corpus_data_cart = PathBuf::from("../../corpus_data/corpus_cartografia.db");

    let db_exists = db_path.exists() || local_db.exists() || corpus_data_db.exists();
    let cart_exists = cartografia_db_path.exists() || local_cart.exists() || corpus_data_cart.exists();

    let resolved_db = if db_path.exists() {
        db_path.to_string_lossy().to_string()
    } else if corpus_data_db.exists() {
        corpus_data_db.to_string_lossy().to_string()
    } else if local_db.exists() {
        local_db.to_string_lossy().to_string()
    } else {
        "Não localizado".to_string()
    };

    let resolved_cart = if cartografia_db_path.exists() {
        cartografia_db_path.to_string_lossy().to_string()
    } else if corpus_data_cart.exists() {
        corpus_data_cart.to_string_lossy().to_string()
    } else if local_cart.exists() {
        local_cart.to_string_lossy().to_string()
    } else {
        "Não localizado".to_string()
    };

    Ok(SystemHealth {
        engine_status: "ONLINE".to_string(),
        os_info: std::env::consts::OS.to_string(),
        app_version: env!("CARGO_PKG_VERSION").to_string(),
        db_exists,
        db_path: resolved_db,
        cartografia_db_exists: cart_exists,
        cartografia_db_path: resolved_cart,
        sidecar_binary_exists: true,
    })
}

#[tauri::command]
pub async fn run_backend_query(
    app: AppHandle,
    acao: String,
    args: Vec<String>,
) -> Result<QueryResultWrapper, String> {
    let start = Instant::now();

    // AppSec: Validação de input para evitar Self-DoS ou buffer overflow local
    if acao.len() > 100 {
        return Err("Ação fornecida excede o limite de caracteres permitido.".to_string());
    }
    for arg in &args {
        if arg.len() > 2000 {
            return Err("Argumento fornecido excede o limite de caracteres permitido.".to_string());
        }
    }
    if args.len() > 20 {
        return Err("Muitos argumentos fornecidos.".to_string());
    }

    let mut full_args = vec![
        "--acao".to_string(),
        acao,
        "--formato".to_string(),
        "json".to_string(),
    ];
    full_args.extend(args);

    let sidecar_command = app
        .shell()
        .sidecar("bin/tycho_backend")
        .map_err(|e| format!("Erro ao inicializar sidecar: {}", e))?;

    let output = sidecar_command
        .args(full_args)
        .output()
        .await
        .map_err(|e| format!("Erro ao executar sidecar Python: {}", e))?;

    let elapsed_ms = start.elapsed().as_millis();

    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        Ok(QueryResultWrapper {
            success: true,
            elapsed_ms,
            data_json: stdout,
            error: None,
        })
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        Ok(QueryResultWrapper {
            success: false,
            elapsed_ms,
            data_json: "[]".to_string(),
            error: Some(stderr),
        })
    }
}
