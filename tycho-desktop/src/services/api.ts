import { Command } from '@tauri-apps/plugin-shell';

export interface SearchResult {
  id: string;
  autor: string;
  texto: string;
  ano: number;
  frase: string;
  arvore: any;
  eh_cartografico: boolean;
}

export const searchCorpus = async (query: string): Promise<SearchResult[]> => {
  try {
    // Chama o executável sidecar compilado (tycho_backend.exe)
    const command = Command.sidecar('bin/tycho_backend', [
      '--acao', 'busca',
      '--label', query,
      '--formato', 'json'
    ]);
    
    const output = await command.execute();
    
    if (output.code !== 0) {
      console.error("Erro no backend:", output.stderr);
      return [];
    }

    const data: SearchResult[] = JSON.parse(output.stdout);
    return data;
  } catch (err) {
    console.error("Erro ao chamar sidecar:", err);
    return [];
  }
};

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

export const listarQuarentena = async (): Promise<QuarentenaItem[]> => {
  try {
    const command = Command.sidecar('bin/tycho_backend', [
      '--acao', 'quarentena_listar',
      '--formato', 'json'
    ]);
    const output = await command.execute();
    if (output.code !== 0) return [];
    return JSON.parse(output.stdout);
  } catch (err) {
    return [];
  }
};

export const resolverQuarentena = async (id: number, acao: string): Promise<boolean> => {
  try {
    const command = Command.sidecar('bin/tycho_backend', [
      '--acao', 'quarentena_resolver',
      '--token', id.toString(),
      '--lemma', acao,
      '--formato', 'json'
    ]);
    const output = await command.execute();
    return output.code === 0;
  } catch (err) {
    return false;
  }
};
