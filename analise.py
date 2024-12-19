import os
from collections import defaultdict, Counter

###############################
# Funções Auxiliares
###############################

def parse_line(line):
    # Divide a linha em partes pelo caractere '|'
    parts = line.strip().split('|')
    # Formato esperado: =|prefix|AS_PATH|peer_ip|...
    # As posições podem variar, mas nos exemplos analisados:
    # - parts[0]: '=' (ou outro indicador)
    # - parts[1]: prefixo
    # - parts[2]: as_path
    # Ajuste caso necessário dependendo do formato final
    if len(parts) < 3:
        return None, None
    prefix = parts[1].strip()
    as_path_str = parts[2].strip()
    # O AS_PATH normalmente é uma sequência de números separada por espaços
    as_path = as_path_str.split()
    return prefix, as_path

def load_snapshot(filename):
    snapshot = {}
    with open(filename, 'r') as f:
        for line in f:
            prefix, as_path = parse_line(line)
            if prefix is not None and as_path is not None:
                snapshot[prefix] = as_path
    return snapshot

def analyze_snapshots(file_list):
    """
    Carrega todos os snapshots e faz análises entre snapshots consecutivos.
    Retorna uma estrutura de dados contendo:
    - snapshots_data: lista de dicionários com informações por snapshot
    - comparisons: lista de resultados da comparação entre pares consecutivos
    """
    # Carrega todos os snapshots em uma lista
    snapshots = []
    for fname in file_list:
        if not os.path.isfile(fname):
            raise FileNotFoundError(f"Arquivo {fname} não encontrado.")
        snap = load_snapshot(fname)
        snapshots.append(snap)
    
    # Informações por snapshot
    snapshots_data = []
    
    # Calcula métricas básicas para cada snapshot
    # Métricas: total de rotas, distribuição do tamanho do AS_PATH,
    # ASes mais frequentes, etc.
    for i, snap in enumerate(snapshots):
        snap_info = {}
        snap_info['filename'] = file_list[i]
        
        # Total de rotas
        snap_info['total_routes'] = len(snap)
        
        # Distribuição do tamanho de AS_PATH
        path_lengths = [len(path) for path in snap.values()]
        if len(path_lengths) > 0:
            avg_path_len = sum(path_lengths) / len(path_lengths)
        else:
            avg_path_len = 0.0
        snap_info['avg_path_length'] = avg_path_len
        
        # Contagem de ASes mais frequentes
        # Vamos contar a frequência de cada AS em todos os paths
        as_counter = Counter()
        for as_list in snap.values():
            as_counter.update(as_list)
        
        # Top 10 ASes mais frequentes
        top_ases = as_counter.most_common(10)
        snap_info['top_ases'] = top_ases
        
        # Guarda dicionário prefix->AS_PATH
        snap_info['snapshot'] = snap
        
        snapshots_data.append(snap_info)
    
    # Comparações entre snapshots consecutivos
    comparisons = []
    
    for i in range(len(snapshots) - 1):
        s1 = snapshots[i]
        s2 = snapshots[i+1]
        
        # Conjuntos de prefixos
        p1 = set(s1.keys())
        p2 = set(s2.keys())
        
        stable = 0
        changed = 0
        disappeared = 0
        new = 0
        
        # Análise dos prefixos do snapshot i (s1)
        for prefix in p1:
            if prefix not in p2:
                # Rota sumiu
                disappeared += 1
            else:
                # Existe em ambos
                if s1[prefix] == s2[prefix]:
                    stable += 1
                else:
                    changed += 1
        
        # Análise dos prefixos que surgiram no snapshot i+1 (s2)
        for prefix in p2:
            if prefix not in p1:
                new += 1
        
        total_s1 = len(s1)
        total_s2 = len(s2)
        
        perc_stable = (stable / total_s1 * 100) if total_s1 > 0 else 0
        perc_changed = (changed / total_s1 * 100) if total_s1 > 0 else 0
        perc_disappeared = (disappeared / total_s1 * 100) if total_s1 > 0 else 0
        # Em new, faz sentido comparar com s2 ou s1. Aqui usaremos s1 para manter padrão.
        perc_new = (new / total_s1 * 100) if total_s1 > 0 else 0
        
        # Estatísticas sobre as rotas estáveis, mudadas, etc. Ex: tamanho do path
        stable_paths_len = [len(s1[p]) for p in p1 if p in p2 and s1[p] == s2[p]] 
        changed_paths_len_before = [len(s1[p]) for p in p1 if p in p2 and s1[p] != s2[p]]
        changed_paths_len_after = [len(s2[p]) for p in p1 if p in p2 and s1[p] != s2[p]]
        
        disappeared_paths_len = [len(s1[p]) for p in p1 if p not in p2]
        new_paths_len = [len(s2[p]) for p in p2 if p not in p1]
        
        def avg_len(lst):
            return sum(lst)/len(lst) if len(lst) > 0 else 0.0
        
        # Cálculo da média de comprimento de AS_PATH para cada categoria
        avg_len_stable = avg_len(stable_paths_len)
        avg_len_changed_before = avg_len(changed_paths_len_before)
        avg_len_changed_after = avg_len(changed_paths_len_after)
        avg_len_disappeared = avg_len(disappeared_paths_len)
        avg_len_new = avg_len(new_paths_len)
        
        # Monta um dicionário com todas as informações da comparação i -> i+1
        comp_info = {
            'from_snapshot': file_list[i],
            'to_snapshot': file_list[i+1],
            'total_s1': total_s1,
            'total_s2': total_s2,
            'stable': stable,
            'changed': changed,
            'disappeared': disappeared,
            'new': new,
            'perc_stable': perc_stable,
            'perc_changed': perc_changed,
            'perc_disappeared': perc_disappeared,
            'perc_new': perc_new,
            'avg_len_stable': avg_len_stable,
            'avg_len_changed_before': avg_len_changed_before,
            'avg_len_changed_after': avg_len_changed_after,
            'avg_len_disappeared': avg_len_disappeared,
            'avg_len_new': avg_len_new
        }
        
        comparisons.append(comp_info)
    
    # Métricas adicionais globais
    # Por exemplo, prefixos presentes em todos os snapshots (evolução completa):
    all_prefixes_sets = [set(snap['snapshot'].keys()) for snap in snapshots_data]
    # Prefixos presentes em todos os snapshots (interseção)
    prefixes_in_all = set.intersection(*all_prefixes_sets) if len(all_prefixes_sets) > 1 else all_prefixes_sets[0]
    
    # Percentual de rotas que permaneceram presentes (não necessariamente estáveis em AS_PATH) em todos os snapshots
    if len(snapshots_data) > 0:
        first_total = snapshots_data[0]['total_routes']
    else:
        first_total = 0
    perc_prefixes_all = (len(prefixes_in_all)/first_total)*100 if first_total > 0 else 0
    
    # Podemos também tentar identificar prefixos totalmente estáveis no caminho,
    # ou seja, prefixos que nunca mudaram o AS_PATH entre nenhum par consecutivo.
    # Para isso, iteramos sobre os prefixos presentes em todos os snapshots e verificamos estabilidade.
    
    totally_stable_prefixes = []
    for p in prefixes_in_all:
        paths = [snapshots_data[i]['snapshot'][p] for i in range(len(snapshots_data))]
        # Verifica se todos os caminhos são iguais
        if all(paths[i] == paths[i+1] for i in range(len(paths)-1)):
            totally_stable_prefixes.append(p)
    perc_totally_stable = (len(totally_stable_prefixes)/first_total)*100 if first_total > 0 else 0
    
    # Retornamos todas as estruturas
    results = {
        'snapshots_data': snapshots_data,
        'comparisons': comparisons,
        'prefixes_in_all': prefixes_in_all,
        'totally_stable_prefixes': totally_stable_prefixes,
        'perc_prefixes_all': perc_prefixes_all,
        'perc_totally_stable': perc_totally_stable
    }
    
    return results


#################################
# Execução do Script (Exemplo)
#################################

if __name__ == "__main__":
    # Lista dos 6 snapshots (ajuste conforme seus arquivos reais)
    file_list = [
        'rib_20241130_2200.out',
        'rib_20241201_0000.out',
        'rib_20241201_0200.out',
        'rib_20241201_0400.out',
        'rib_20241201_0600.out',
        'rib_20241201_1800.out'
    ]
    
    try:
        results = analyze_snapshots(file_list)
    except FileNotFoundError as e:
        print(e)
        exit(1)
    
    ###############################
    # Impressão dos resultados
    ###############################
    
    print("=== ANÁLISE DE ESTABILIDADE BGP COM MÚLTIPLOS SNAPSHOTS ===\n")
    
    # Imprimir estatísticas por snapshot
    for i, snap_info in enumerate(results['snapshots_data']):
        print(f"Snapshot {i+1}: {snap_info['filename']}")
        print(f"  Total de rotas: {snap_info['total_routes']}")
        print(f"  Tamanho médio do AS_PATH: {snap_info['avg_path_length']:.2f}")
        print("  Top 10 ASes mais frequentes (AS, contagem):")
        for asn, count in snap_info['top_ases']:
            print(f"    {asn}: {count}")
        print()
    
    # Imprimir comparações entre snapshots consecutivos
    print("=== Comparações entre snapshots consecutivos ===\n")
    for comp in results['comparisons']:
        print(f"Comparação: {comp['from_snapshot']} -> {comp['to_snapshot']}")
        print(f"  Total no snapshot inicial: {comp['total_s1']} | Total no snapshot final: {comp['total_s2']}")
        print(f"  Estáveis: {comp['stable']} ({comp['perc_stable']:.2f}%)")
        print(f"  Mudaram AS_PATH: {comp['changed']} ({comp['perc_changed']:.2f}%)")
        print(f"  Desapareceram: {comp['disappeared']} ({comp['perc_disappeared']:.2f}%)")
        print(f"  Novas no snapshot final: {comp['new']} ({comp['perc_new']:.2f}%)")
        print(f"  Comprimento médio AS_PATH (estáveis): {comp['avg_len_stable']:.2f}")
        print(f"  Comprimento médio AS_PATH (antes da mudança): {comp['avg_len_changed_before']:.2f}")
        print(f"  Comprimento médio AS_PATH (depois da mudança): {comp['avg_len_changed_after']:.2f}")
        print(f"  Comprimento médio AS_PATH (rotas desaparecidas): {comp['avg_len_disappeared']:.2f}")
        print(f"  Comprimento médio AS_PATH (rotas novas): {comp['avg_len_new']:.2f}")
        print()
    
    # Métricas globais
    print("=== Métricas Globais ===")
    print(f"Prefixos presentes em TODOS os snapshots: {len(results['prefixes_in_all'])}")
    print(f"Percentual de prefixos do primeiro snapshot presentes em todos: {results['perc_prefixes_all']:.2f}%")
    print(f"Prefixos totalmente estáveis (AS_PATH inalterado em todos os snapshots): {len(results['totally_stable_prefixes'])}")
    print(f"Percentual totalmente estável: {results['perc_totally_stable']:.2f}%")
    print()
    
    print("Esses resultados fornecem uma visão abrangente sobre a evolução das rotas BGP ao longo dos 6 snapshots,")
    print("permitindo comparações ricas, confecção de gráficos e insights sobre a estabilidade e mudanças no plano de controle da Internet.")
