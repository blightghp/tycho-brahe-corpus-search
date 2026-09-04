use crate::m4_bridge::{
    build_m4_sidecar_args, m4_artifact_path, parse_m4_sidecar_response, resolve_m4_artifact,
    M4BridgeError, M4SearchCriteria, M4SearchResponse, M4_SIDECAR_NAME,
};
use crate::models::{QueryResultWrapper, SystemHealth};
use std::path::{Path, PathBuf};
use std::time::Instant;
use tauri::{AppHandle, Manager};
use tauri_plugin_shell::ShellExt;

/// Localiza referências históricas apenas para diagnóstico e para as telas
/// legadas. A rota M4 nunca usa esses arquivos como fallback.
fn locate_legacy_database(app_data_dir: &Path, filename: &str) -> Option<PathBuf> {
    [
        app_data_dir.join(filename),
        PathBuf::from(filename),
        PathBuf::from("../../corpus_data").join(filename),
    ]
    .into_iter()
    .find(|candidate| candidate.is_file())
}

#[tauri::command]
pub async fn check_system_health(app: AppHandle) -> Result<SystemHealth, String> {
    let app_data_dir = app
        .path()
        .app_data_dir()
        .unwrap_or_else(|_| PathBuf::from("."));
    let expected_m4_artifact = m4_artifact_path(&app_data_dir);

    Ok(SystemHealth {
        engine_status: "ONLINE".to_string(),
        os_info: std::env::consts::OS.to_string(),
        app_version: env!("CARGO_PKG_VERSION").to_string(),
        m4_artifact_available: resolve_m4_artifact(&app_data_dir).is_ok(),
        m4_artifact_path: expected_m4_artifact.to_string_lossy().to_string(),
        legacy_fase3_available: locate_legacy_database(&app_data_dir, "corpus_fase3.db").is_some(),
        legacy_cartography_available: locate_legacy_database(
            &app_data_dir,
            "corpus_cartografia.db",
        )
        .is_some(),
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

/// Executa a busca evidencial Marco 4 por uma ponte separada do sidecar legado.
///
/// O payload IPC é deserializado para `M4SearchCriteria`, que nega campos
/// extras. Em particular, a interface não pode passar caminhos de banco,
/// argumentos livres ou o sinalizador caro `--verify-source`. O único M3
/// aceito é o arquivo previamente provisionado sob o diretório de dados da
/// aplicação e validado pela pré-condição do próprio sidecar.
#[tauri::command]
pub async fn run_m4_search(app: AppHandle, criteria: M4SearchCriteria) -> M4SearchResponse {
    let normalized = match criteria.normalize() {
        Ok(value) => value,
        Err(error) => return error.failure(),
    };

    let app_data_dir = match app.path().app_data_dir() {
        Ok(path) => path,
        Err(_) => {
            return M4BridgeError::new(
                "M4_ARTIFACT_UNAVAILABLE",
                "Não foi possível localizar o diretório controlado de dados do aplicativo.",
            )
            .failure();
        }
    };
    let artifact_path = match resolve_m4_artifact(&app_data_dir) {
        Ok(path) => path,
        Err(error) => return error.failure(),
    };
    let args = match build_m4_sidecar_args(&normalized, &artifact_path) {
        Ok(value) => value,
        Err(error) => return error.failure(),
    };

    let sidecar_command = match app.shell().sidecar(M4_SIDECAR_NAME) {
        Ok(command) => command,
        Err(_) => {
            return M4BridgeError::new(
                "M4_SIDECAR_UNAVAILABLE",
                "O sidecar dedicado da busca Marco 4 não está instalado neste aplicativo.",
            )
            .failure();
        }
    };
    let output = match sidecar_command.args(args).output().await {
        Ok(value) => value,
        Err(_) => {
            return M4BridgeError::new(
                "M4_SIDECAR_UNAVAILABLE",
                "Não foi possível executar o sidecar dedicado da busca Marco 4.",
            )
            .failure();
        }
    };

    if !output.stdout.is_empty() {
        match parse_m4_sidecar_response(&output.stdout) {
            Ok(response) => return response,
            Err(error) if output.status.success() => return error.failure(),
            Err(_) => {}
        }
    }

    M4BridgeError::new(
        "M4_SIDECAR_PROTOCOL",
        "O sidecar Marco 4 não retornou uma resposta de busca compatível.",
    )
    .failure()
}
