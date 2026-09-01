import { invoke } from '@tauri-apps/api/core';
import { Command } from '@tauri-apps/plugin-shell';

export {
  buildM4SearchCommand,
  DEFAULT_M4_SEARCH_LIMIT,
  M4_SEARCH_CONTRACT_VERSION,
  M4_SEARCH_NOT_CONNECTED,
  M4_ENTITY_TYPES,
  MAX_M4_FILTER_LENGTH,
  MAX_M4_SEARCH_LIMIT,
  m4ReviewNotice,
  M4SearchCriteriaError,
} from './m4SearchContract';
export type {
  M4AnalysisIdentity,
  M4Anchor,
  M4Decision,
  M4Entity,
  M4EntityType,
  M4Evidence,
  M4EvidenceType,
  M4Origin,
  M4SearchCommand,
  M4SearchCriteria,
  M4SearchFailure,
  M4SearchQuery,
  M4SearchResponse,
  M4SearchResult,
  M4SearchSuccess,
  M4SearchValidation,
} from './m4SearchContract';

export interface SystemHealth {
  engine_status: string;
  os_info: string;
  app_version: string;
  db_exists: boolean;
  db_path: string;
  cartografia_db_exists: boolean;
  cartografia_db_path: string;
  sidecar_binary_exists: boolean;
}

export interface QueryResultWrapper {
  success: boolean;
  elapsed_ms: number;
  data_json: string;
  error?: string;
}

export interface SearchResult {
  id: string;
  autor: string;
  texto: string;
  ano: number;
  frase: string;
  arvore: any;
  eh_cartografico: boolean;
}

export interface QuarentenaItem {
  id: number;
  arquivo: string;
  sent_id_externo: string;
  arvore_original: string;
  arvore_sugerida: string;
  motivo_anomalia: string;
  tipo_anomalia: string;
  status: string;
}

export interface TokenCartografico {
  indice: number;
  termo: string;
  lema: string;
  pos: string;
  dominio_id: number;
  dominio_nome: string;
  projecao: string;
  papel_gerativo: string;
  eh_cartografico: boolean;
  trilha_arvore?: string;
}

export const getSystemHealth = async (): Promise<SystemHealth> => {
  try {
    return await invoke<SystemHealth>('check_system_health');
  } catch (err) {
    console.error('Falha ao checar saúde do motor Rust:', err);
    return {
      engine_status: 'OFFLINE',
      os_info: 'unknown',
      app_version: '0.1.0',
      db_exists: false,
      db_path: '',
      cartografia_db_exists: false,
      cartografia_db_path: '',
      sidecar_binary_exists: false,
    };
  }
};

export const searchCorpus = async (query: string): Promise<SearchResult[]> => {
  try {
    const res = await invoke<QueryResultWrapper>('run_backend_query', {
      acao: 'busca',
      args: ['--label', query],
    });

    if (res.success) {
      return JSON.parse(res.data_json);
    }
    console.warn('Erro retornado pelo motor Rust:', res.error);
    return [];
  } catch (err) {
    console.warn('Fallback para shell plugin direto:', err);
    try {
      const command = Command.sidecar('bin/tycho_backend', [
        '--acao', 'busca',
        '--label', query,
        '--formato', 'json',
      ]);
      const output = await command.execute();
      if (output.code === 0) {
        return JSON.parse(output.stdout);
      }
    } catch (fallbackErr) {
      console.error('Falha geral no IPC:', fallbackErr);
    }
    return [];
  }
};

export const tokenizarSentenca = async (texto: string): Promise<TokenCartografico[]> => {
  try {
    const res = await invoke<QueryResultWrapper>('run_backend_query', {
      acao: 'tokenizar',
      args: ['--token', texto],
    });

    if (res.success) {
      return JSON.parse(res.data_json);
    }
    return [];
  } catch (err) {
    try {
      const command = Command.sidecar('bin/tycho_backend', [
        '--acao', 'tokenizar',
        '--token', texto,
        '--formato', 'json',
      ]);
      const output = await command.execute();
      if (output.code === 0) {
        return JSON.parse(output.stdout);
      }
    } catch (fallbackErr) {
      console.error('Falha ao tokenizar sentenca:', fallbackErr);
    }
    return [];
  }
};

export const listarQuarentena = async (): Promise<QuarentenaItem[]> => {
  try {
    const res = await invoke<QueryResultWrapper>('run_backend_query', {
      acao: 'quarentena_listar',
      args: [],
    });
    if (res.success) {
      return JSON.parse(res.data_json);
    }
    return [];
  } catch (err) {
    try {
      const command = Command.sidecar('bin/tycho_backend', [
        '--acao', 'quarentena_listar',
        '--formato', 'json',
      ]);
      const output = await command.execute();
      if (output.code === 0) return JSON.parse(output.stdout);
    } catch (fallbackErr) {
      console.error(fallbackErr);
    }
    return [];
  }
};

export const resolverQuarentena = async (id: number, acao: string): Promise<boolean> => {
  try {
    const res = await invoke<QueryResultWrapper>('run_backend_query', {
      acao: 'quarentena_resolver',
      args: ['--token', id.toString(), '--lemma', acao],
    });
    return res.success;
  } catch (err) {
    try {
      const command = Command.sidecar('bin/tycho_backend', [
        '--acao', 'quarentena_resolver',
        '--token', id.toString(),
        '--lemma', acao,
        '--formato', 'json',
      ]);
      const output = await command.execute();
      return output.code === 0;
    } catch (fallbackErr) {
      return false;
    }
  }
};
