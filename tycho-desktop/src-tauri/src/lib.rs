pub mod models;
pub mod commands;

use commands::{check_system_health, run_backend_query};

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Tycho Brahe Core Engine: Olá, {}!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            greet,
            check_system_health,
            run_backend_query
        ])
        .run(tauri::generate_context!())
        .expect("Erro fatal ao executar a aplicação Tycho Brahe Desktop");
}
