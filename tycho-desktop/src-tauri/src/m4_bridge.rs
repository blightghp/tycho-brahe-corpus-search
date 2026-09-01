//! Ponte restrita entre o IPC Tauri e a busca evidencial Marco 4.
//!
//! A interface nunca informa caminhos, argumentos livres ou comandos. Este
//! módulo aceita somente os critérios estabelecidos pelo contrato M4, resolve
//! um único artefato promovido dentro do diretório de dados do aplicativo e
//! gera um vetor de argumentos sem invocar uma shell.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fmt;
use std::fs;
use std::path::{Path, PathBuf};

pub const M4_SIDECAR_NAME: &str = "bin/tycho_m4_search";
pub const M4_DEFAULT_LIMIT: u16 = 50;
pub const M4_MAX_LIMIT: u16 = 500;
pub const M4_MAX_FILTER_LENGTH: usize = 512;
pub const M4_MAX_SIDECAR_OUTPUT_BYTES: usize = 16 * 1024 * 1024;

/// Caminho relativo fixo do artefato M3 promovido no armazenamento da app.
///
/// O Marco 5 não copia, baixa ou empacota o banco. O provisionador controlado
/// instala um artefato já validado exatamente neste local.
pub const M4_ARTIFACT_RELATIVE_PATH: [&str; 3] =
    ["artifacts", "marco3", "corpus_marco3_evidencial.sqlite"];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum M4EntityType {
    #[serde(rename = "EXCLUSAO")]
    Exclusao,
    #[serde(rename = "NUCLEO_LEXICAL")]
    NucleoLexical,
    #[serde(rename = "NUCLEO_FUNCIONAL")]
    NucleoFuncional,
    #[serde(rename = "NUCLEO_FRONTEIRA")]
    NucleoFronteira,
    #[serde(rename = "EVIDENCIA_AUXILIAR")]
    EvidenciaAuxiliar,
    #[serde(rename = "PROJECAO_FONTE")]
    ProjecaoFonte,
    #[serde(rename = "EVIDENCIA_CARTOGRAFICA")]
    EvidenciaCartografica,
}

impl M4EntityType {
    fn as_contract_value(self) -> &'static str {
        match self {
            Self::Exclusao => "EXCLUSAO",
            Self::NucleoLexical => "NUCLEO_LEXICAL",
            Self::NucleoFuncional => "NUCLEO_FUNCIONAL",
            Self::NucleoFronteira => "NUCLEO_FRONTEIRA",
            Self::EvidenciaAuxiliar => "EVIDENCIA_AUXILIAR",
            Self::ProjecaoFonte => "PROJECAO_FONTE",
            Self::EvidenciaCartografica => "EVIDENCIA_CARTOGRAFICA",
        }
    }
}

/// Único payload aceito no IPC para a busca Marco 4.
///
/// `deny_unknown_fields` impede que uma UI envie `db`, `args`, `command`,
/// `sourceDb` ou qualquer outra opção que não pertença ao contrato M4.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct M4SearchCriteria {
    #[serde(default)]
    pub entity_type: Option<M4EntityType>,
    #[serde(default)]
    pub analytical_label: Option<String>,
    #[serde(default)]
    pub projection: Option<String>,
    #[serde(default)]
    pub token: Option<String>,
    #[serde(default)]
    pub rule_id: Option<String>,
    #[serde(default)]
    pub limit: Option<u16>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NormalizedM4SearchCriteria {
    pub entity_type: Option<M4EntityType>,
    pub analytical_label: Option<String>,
    pub projection: Option<String>,
    pub token: Option<String>,
    pub rule_id: Option<String>,
    pub limit: u16,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct M4BridgeError {
    pub code: &'static str,
    pub message: String,
}

impl M4BridgeError {
    pub fn new(code: &'static str, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
        }
    }

    pub fn failure(&self) -> M4SearchResponse {
        M4SearchResponse::Failure(M4SearchFailure {
            ok: false,
            code: Some(self.code.to_string()),
            error: self.message.clone(),
        })
    }
}

impl fmt::Display for M4BridgeError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}: {}", self.code, self.message)
    }
}

impl std::error::Error for M4BridgeError {}

impl M4SearchCriteria {
    pub fn normalize(&self) -> Result<NormalizedM4SearchCriteria, M4BridgeError> {
        let analytical_label =
            normalize_filter("analyticalLabel", self.analytical_label.as_deref())?;
        let projection = normalize_filter("projection", self.projection.as_deref())?;
        let token = normalize_filter("token", self.token.as_deref())?;
        let rule_id = normalize_filter("ruleId", self.rule_id.as_deref())?;
        let limit = self.limit.unwrap_or(M4_DEFAULT_LIMIT);

        if !(1..=M4_MAX_LIMIT).contains(&limit) {
            return Err(M4BridgeError::new(
                "M4_INVALID_CRITERIA",
                format!("O limite deve ser um inteiro entre 1 e {M4_MAX_LIMIT}."),
            ));
        }
        if self.entity_type.is_none()
            && analytical_label.is_none()
            && projection.is_none()
            && token.is_none()
            && rule_id.is_none()
        {
            return Err(M4BridgeError::new(
                "M4_INVALID_CRITERIA",
                "Informe ao menos um filtro evidencial antes de consultar o Marco 4.",
            ));
        }

        Ok(NormalizedM4SearchCriteria {
            entity_type: self.entity_type,
            analytical_label,
            projection,
            token,
            rule_id,
            limit,
        })
    }
}

fn normalize_filter(name: &str, value: Option<&str>) -> Result<Option<String>, M4BridgeError> {
    let Some(value) = value else {
        return Ok(None);
    };
    let normalized = value.trim();
    if normalized.is_empty() {
        return Ok(None);
    }
    if normalized.chars().count() > M4_MAX_FILTER_LENGTH {
        return Err(M4BridgeError::new(
            "M4_INVALID_CRITERIA",
            format!("O filtro {name} excede {M4_MAX_FILTER_LENGTH} caracteres."),
        ));
    }
    if normalized.contains('\0') {
        return Err(M4BridgeError::new(
            "M4_INVALID_CRITERIA",
            format!("O filtro {name} contém um caractere inválido."),
        ));
    }
    // Mesmo sem shell, valores que começam por hífen poderiam ser interpretados
    // pelo argparse como uma nova opção do sidecar. Rótulos M4 válidos não
    // exigem esse formato; rejeitá-los torna o vetor de argumentos inequívoco.
    if normalized.starts_with('-') {
        return Err(M4BridgeError::new(
            "M4_INVALID_CRITERIA",
            format!("O filtro {name} não pode iniciar com hífen."),
        ));
    }
    Ok(Some(normalized.to_owned()))
}

/// Resolve somente o arquivo M3 fixo sob o diretório de dados do aplicativo.
///
/// Não há fallback para CWD, bancos legados, `%TEMP%`, variáveis de ambiente
/// ou caminhos enviados pela UI. A ausência é um estado esperado até existir
/// um artefato promovido instalado pelo provisionador controlado, e não deve
/// ser mascarada por outro banco experimental.
pub fn resolve_m4_artifact(app_data_dir: &Path) -> Result<PathBuf, M4BridgeError> {
    let artifact_path = M4_ARTIFACT_RELATIVE_PATH
        .iter()
        .fold(app_data_dir.to_path_buf(), |path, segment| {
            path.join(segment)
        });

    if !artifact_path.is_file() {
        return Err(M4BridgeError::new(
            "M4_ARTIFACT_UNAVAILABLE",
            "O artefato Marco 3 promovido ainda não foi provisionado para este aplicativo. A busca evidencial permanece indisponível até a instalação verificada do artefato.",
        ));
    }

    let canonical_root = fs::canonicalize(app_data_dir).map_err(|_| {
        M4BridgeError::new(
            "M4_ARTIFACT_UNAVAILABLE",
            "Não foi possível verificar o diretório controlado do artefato Marco 3.",
        )
    })?;
    let canonical_artifact = fs::canonicalize(&artifact_path).map_err(|_| {
        M4BridgeError::new(
            "M4_ARTIFACT_UNAVAILABLE",
            "Não foi possível verificar o artefato Marco 3 provisionado.",
        )
    })?;

    if !canonical_artifact.starts_with(&canonical_root) {
        return Err(M4BridgeError::new(
            "M4_ARTIFACT_UNAVAILABLE",
            "O artefato Marco 3 não está contido na localização controlada do aplicativo.",
        ));
    }

    Ok(canonical_artifact)
}

/// Monta os argumentos do CLI M4 sem interpolação em uma shell.
pub fn build_m4_sidecar_args(
    criteria: &NormalizedM4SearchCriteria,
    artifact_path: &Path,
) -> Result<Vec<String>, M4BridgeError> {
    let artifact = artifact_path.to_str().ok_or_else(|| {
        M4BridgeError::new(
            "M4_ARTIFACT_UNAVAILABLE",
            "O caminho controlado do artefato Marco 3 não é representável para o sidecar.",
        )
    })?;
    let mut args = vec![
        "search".to_string(),
        "--db".to_string(),
        artifact.to_string(),
    ];

    if let Some(entity_type) = criteria.entity_type {
        args.push("--entity-type".to_string());
        args.push(entity_type.as_contract_value().to_string());
    }
    append_option(&mut args, "--label", criteria.analytical_label.as_deref());
    append_option(&mut args, "--projection", criteria.projection.as_deref());
    append_option(&mut args, "--token", criteria.token.as_deref());
    append_option(&mut args, "--rule", criteria.rule_id.as_deref());
    args.push("--limit".to_string());
    args.push(criteria.limit.to_string());
    Ok(args)
}

fn append_option(args: &mut Vec<String>, flag: &str, value: Option<&str>) {
    if let Some(value) = value {
        args.push(flag.to_string());
        args.push(value.to_string());
    }
}

#[derive(Debug, Clone, Serialize)]
#[serde(untagged)]
pub enum M4SearchResponse {
    Success(M4SearchSuccess),
    Failure(M4SearchFailure),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct M4SearchFailure {
    pub ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub code: Option<String>,
    pub error: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct M4SearchSuccess {
    pub ok: bool,
    pub analysis: M4AnalysisIdentity,
    pub query: M4SearchQuery,
    pub validation: M4SearchValidation,
    pub result_count: usize,
    pub results: Vec<M4SearchResult>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct M4AnalysisIdentity {
    pub analysis_id: i64,
    pub schema_version: String,
    pub engine_version: String,
    pub engine_sha256: String,
    pub ruleset_version: String,
    pub ruleset_sha256: String,
    pub source_database_sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct M4SearchQuery {
    pub entity_type: Option<M4EntityType>,
    pub label: Option<String>,
    pub projection: Option<String>,
    pub token: Option<String>,
    pub rule: Option<String>,
    pub limit: u16,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct M4SearchValidation {
    pub mode: String,
    pub full_source_validation: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct M4SearchResult {
    pub analysis: M4AnalysisIdentity,
    pub origin: M4Origin,
    pub anchor: M4Anchor,
    pub entity: M4Entity,
    pub decision: M4Decision,
    pub evidence: Vec<M4Evidence>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct M4Origin {
    pub relative_path: String,
    pub document_id: i64,
    pub block_id: i64,
    pub candidate_ordinal: i64,
    pub block_ordinal: i64,
    pub block_sha256: String,
    pub import_result: String,
    pub analysis_scope_status: String,
    pub sentence_id: i64,
    pub external_id: Option<String>,
    pub root_label: String,
    pub structure_class: String,
    pub tree_sha256: String,
    pub leaves_sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct M4Anchor {
    pub node_id: i64,
    pub source_label: String,
    pub source_base: String,
    pub source_function: Option<String>,
    pub preorder: i64,
    pub leaf_ordinal: Option<i64>,
    pub token: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct M4Entity {
    pub entity_id: i64,
    #[serde(rename = "type")]
    pub entity_type: M4EntityType,
    pub analytical_label: String,
    pub source_projection: Option<String>,
    pub evidenced_projection: Option<String>,
    pub order: i64,
    pub details: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct M4Decision {
    pub decision_id: i64,
    pub rule_id: String,
    pub confidence: f64,
    pub confidence_method: String,
    pub evidence_status: String,
    pub review_status: String,
    pub justification: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct M4Evidence {
    pub evidence_id: i64,
    #[serde(rename = "type")]
    pub evidence_type: String,
    pub ordinal: i64,
    pub value: Value,
    pub sha256: String,
    pub description: String,
}

/// Decodifica o stdout do sidecar e aceita apenas respostas do contrato M4.
pub fn parse_m4_sidecar_response(stdout: &[u8]) -> Result<M4SearchResponse, M4BridgeError> {
    if stdout.len() > M4_MAX_SIDECAR_OUTPUT_BYTES {
        return Err(M4BridgeError::new(
            "M4_SIDECAR_PROTOCOL",
            "A resposta do sidecar Marco 4 excedeu o limite seguro da ponte.",
        ));
    }
    let payload: Value = serde_json::from_slice(stdout).map_err(|_| {
        M4BridgeError::new(
            "M4_SIDECAR_PROTOCOL",
            "O sidecar Marco 4 não retornou JSON válido do contrato de busca.",
        )
    })?;
    let ok = payload.get("ok").and_then(Value::as_bool).ok_or_else(|| {
        M4BridgeError::new(
            "M4_SIDECAR_PROTOCOL",
            "O sidecar Marco 4 retornou JSON sem o estado obrigatório da busca.",
        )
    })?;

    if ok {
        let success: M4SearchSuccess = serde_json::from_value(payload).map_err(|_| {
            M4BridgeError::new(
                "M4_SIDECAR_PROTOCOL",
                "O sidecar Marco 4 retornou uma resposta de sucesso incompatível com o contrato.",
            )
        })?;
        if !success.ok
            || success.result_count != success.results.len()
            || success.result_count > M4_MAX_LIMIT as usize
            || success.query.limit == 0
            || success.query.limit > M4_MAX_LIMIT
            || success.result_count > success.query.limit as usize
        {
            return Err(M4BridgeError::new(
                "M4_SIDECAR_PROTOCOL",
                "O sidecar Marco 4 retornou contagens incompatíveis com o contrato de busca.",
            ));
        }
        return Ok(M4SearchResponse::Success(success));
    }

    let failure: M4SearchFailure = serde_json::from_value(payload).map_err(|_| {
        M4BridgeError::new(
            "M4_SIDECAR_PROTOCOL",
            "O sidecar Marco 4 retornou uma falha incompatível com o contrato de busca.",
        )
    })?;
    if failure.ok || failure.error.trim().is_empty() {
        return Err(M4BridgeError::new(
            "M4_SIDECAR_PROTOCOL",
            "O sidecar Marco 4 retornou uma falha sem mensagem válida.",
        ));
    }
    Ok(M4SearchResponse::Failure(M4SearchFailure {
        ok: false,
        // Não propaga uma mensagem potencialmente longa ou com caminhos locais
        // impressa pelo processo filho. A ponte expõe uma orientação estável.
        code: Some("M4_SIDECAR_REJECTED".to_string()),
        error: "O sidecar Marco 4 recusou a consulta; confirme que o artefato é um Marco 3 promovido compatível.".to_string(),
    }))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::time::{SystemTime, UNIX_EPOCH};

    struct TestDirectory(PathBuf);

    impl Drop for TestDirectory {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    fn temporary_directory() -> TestDirectory {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock")
            .as_nanos();
        let path = std::env::temp_dir().join(format!(
            "tycho-m4-bridge-test-{}-{nonce}",
            std::process::id()
        ));
        fs::create_dir_all(&path).expect("create temporary test directory");
        TestDirectory(path)
    }

    fn success_payload() -> Vec<u8> {
        serde_json::to_vec(&json!({
            "ok": true,
            "analysis": {
                "analysis_id": 1,
                "schema_version": "m3-evidential-v1",
                "engine_version": "m3",
                "engine_sha256": "a",
                "ruleset_version": "v1",
                "ruleset_sha256": "b",
                "source_database_sha256": "c"
            },
            "query": {
                "entity_type": "NUCLEO_LEXICAL",
                "label": null,
                "projection": null,
                "token": "rei",
                "rule": null,
                "limit": 50
            },
            "validation": {
                "mode": "precondicao_m3_promovido",
                "full_source_validation": false
            },
            "result_count": 1,
            "results": [{
                "analysis": {
                    "analysis_id": 1,
                    "schema_version": "m3-evidential-v1",
                    "engine_version": "m3",
                    "engine_sha256": "a",
                    "ruleset_version": "v1",
                    "ruleset_sha256": "b",
                    "source_database_sha256": "c"
                },
                "origin": {
                    "relative_path": "doc.psd",
                    "document_id": 1,
                    "block_id": 2,
                    "candidate_ordinal": 1,
                    "block_ordinal": 3,
                    "block_sha256": "d",
                    "import_result": "IMPORTADO",
                    "analysis_scope_status": "ANALISADA",
                    "sentence_id": 4,
                    "external_id": null,
                    "root_label": "CP",
                    "structure_class": "SENTENCA",
                    "tree_sha256": "e",
                    "leaves_sha256": "f"
                },
                "anchor": {
                    "node_id": 5,
                    "source_label": "N",
                    "source_base": "N",
                    "source_function": null,
                    "preorder": 6,
                    "leaf_ordinal": 7,
                    "token": "rei"
                },
                "entity": {
                    "entity_id": 8,
                    "type": "NUCLEO_LEXICAL",
                    "analytical_label": "N",
                    "source_projection": "NP",
                    "evidenced_projection": null,
                    "order": 9,
                    "details": {}
                },
                "decision": {
                    "decision_id": 10,
                    "rule_id": "M4-TEST",
                    "confidence": 0.8,
                    "confidence_method": "HEURISTICA",
                    "evidence_status": "EVIDENCIADA",
                    "review_status": "PENDENTE",
                    "justification": "fixture"
                },
                "evidence": [{
                    "evidence_id": 11,
                    "type": "TOKEN",
                    "ordinal": 1,
                    "value": "rei",
                    "sha256": "g",
                    "description": "fixture"
                }]
            }]
        }))
        .expect("serialize fixture")
    }

    #[test]
    fn criteria_are_allowlisted_and_normalized() {
        let criteria: M4SearchCriteria = serde_json::from_value(json!({
            "entityType": "NUCLEO_LEXICAL",
            "analyticalLabel": "  N  ",
            "token": " rei ",
            "limit": 50
        }))
        .expect("deserialize allowed criteria");
        let normalized = criteria.normalize().expect("normalize criteria");
        assert_eq!(normalized.entity_type, Some(M4EntityType::NucleoLexical));
        assert_eq!(normalized.analytical_label.as_deref(), Some("N"));
        assert_eq!(normalized.token.as_deref(), Some("rei"));
        assert_eq!(normalized.limit, 50);

        let unknown = serde_json::from_value::<M4SearchCriteria>(json!({
            "token": "rei",
            "db": "C:/fora-do-controle.sqlite"
        }));
        assert!(
            unknown.is_err(),
            "IPC must reject database paths and unknown fields"
        );
    }

    #[test]
    fn criteria_reject_ambiguous_arguments_and_missing_filter() {
        let injected = M4SearchCriteria {
            entity_type: None,
            analytical_label: None,
            projection: None,
            token: Some("--db=C:/fora-do-controle.sqlite".to_string()),
            rule_id: None,
            limit: None,
        };
        assert_eq!(
            injected.normalize().unwrap_err().code,
            "M4_INVALID_CRITERIA"
        );

        let empty = M4SearchCriteria {
            entity_type: None,
            analytical_label: Some("   ".to_string()),
            projection: None,
            token: None,
            rule_id: None,
            limit: None,
        };
        assert_eq!(empty.normalize().unwrap_err().code, "M4_INVALID_CRITERIA");
    }

    #[test]
    fn sidecar_arguments_are_fixed_and_positional() {
        let criteria = M4SearchCriteria {
            entity_type: Some(M4EntityType::NucleoLexical),
            analytical_label: Some("N".to_string()),
            projection: Some("NP".to_string()),
            token: Some("rei".to_string()),
            rule_id: Some("M3-LEX-01".to_string()),
            limit: Some(12),
        }
        .normalize()
        .expect("normalize");
        let args = build_m4_sidecar_args(&criteria, Path::new("C:/controlled/m3.sqlite"))
            .expect("build args");
        assert_eq!(
            args,
            vec![
                "search",
                "--db",
                "C:/controlled/m3.sqlite",
                "--entity-type",
                "NUCLEO_LEXICAL",
                "--label",
                "N",
                "--projection",
                "NP",
                "--token",
                "rei",
                "--rule",
                "M3-LEX-01",
                "--limit",
                "12"
            ]
        );
    }

    #[test]
    fn resolver_uses_only_the_controlled_fixed_location() {
        let test_directory = temporary_directory();
        let missing = resolve_m4_artifact(&test_directory.0).expect_err("missing artifact");
        assert_eq!(missing.code, "M4_ARTIFACT_UNAVAILABLE");

        let artifact = M4_ARTIFACT_RELATIVE_PATH
            .iter()
            .fold(test_directory.0.clone(), |path, segment| path.join(segment));
        fs::create_dir_all(artifact.parent().expect("artifact parent")).expect("create parent");
        fs::write(&artifact, b"fixture").expect("create artifact");
        assert_eq!(
            resolve_m4_artifact(&test_directory.0).expect("resolve artifact"),
            fs::canonicalize(&artifact).expect("canonical artifact")
        );
    }

    #[test]
    fn sidecar_success_is_decoded_as_the_m4_contract() {
        let response = parse_m4_sidecar_response(&success_payload()).expect("parse response");
        match response {
            M4SearchResponse::Success(success) => {
                assert!(success.ok);
                assert_eq!(success.result_count, 1);
                assert_eq!(success.results[0].anchor.token.as_deref(), Some("rei"));
            }
            M4SearchResponse::Failure(_) => panic!("expected success"),
        }
    }

    #[test]
    fn malformed_or_inconsistent_sidecar_output_is_rejected() {
        assert_eq!(
            parse_m4_sidecar_response(b"not-json").unwrap_err().code,
            "M4_SIDECAR_PROTOCOL"
        );
        let mut inconsistent: Value =
            serde_json::from_slice(&success_payload()).expect("fixture json");
        inconsistent["result_count"] = json!(2);
        let bytes = serde_json::to_vec(&inconsistent).expect("serialize inconsistent fixture");
        assert_eq!(
            parse_m4_sidecar_response(&bytes).unwrap_err().code,
            "M4_SIDECAR_PROTOCOL"
        );
    }
}
