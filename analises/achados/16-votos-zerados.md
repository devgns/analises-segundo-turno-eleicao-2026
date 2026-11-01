# Seções sem votos para o candidato

Reprodução: `uv run python analises/16_votos_zerados.py`. Saída: `site/public/data/ch09/votos-zerados.json`. São contagens de boletins de urna, com exterior; seções sem nenhum voto válido no turno são excluídas. No primeiro turno, zero para um candidato não significa que todos os votos foram para o outro finalista.

| Eleição | Candidato | 1º turno | 2º turno |
|---|---|---:|---:|
| 2026 | Flávio Bolsonaro | 81 | 106 |
| 2026 | Lula | 8 | 4 |
| 2022 | Jair Bolsonaro | 161 | 143 |
| 2022 | Lula | 1 | 4 |

Em 2026, uma das 81 seções com zero para Flávio no primeiro turno não tem correspondente no segundo: a comparação entre turnos usa 80 seções com zero no primeiro turno entre as 499.205 seções pareadas. Das 106 com zero para Flávio no segundo, 50 também eram zero no primeiro; nas 56 restantes ele teve no primeiro turno 118 votos ao todo, com máximo 16 por seção. As 106 somam 14.860 votos válidos no segundo turno e mediana de 124,5. Lula teve pelo menos 90% dos votos dos dois finalistas no primeiro turno em todas elas.

Em 2022, 85 das 143 seções com zero para Jair Bolsonaro no segundo turno também tinham zero no primeiro; as outras 58 somavam 88 votos nele no primeiro turno. O máximo por seção era 5. Em 142 das 143, Lula teve ao menos 90% dos votos dos dois finalistas no primeiro turno.

Para as 106 seções de 2026, 61 possuem a mesma chave de UF, município TSE, zona e seção nos dois turnos de 2022. Dessas, 23 tiveram zero para Jair Bolsonaro no segundo turno de 2022 e 16 tiveram zero em ambos os turnos daquele ano. As outras 45 não foram encontradas pela chave; isso não implica que antes não existisse uma seção equivalente. Mesmo uma chave repetida não garante que os mesmos eleitores ou local físico permaneceram. Jair e Flávio são pessoas diferentes.

O modelo do capítulo 7 usa apenas seções com referência local ou municipal calculável. Em 2022, duas seções do exterior com zero para Bolsonaro não têm essa referência e não entram no modelo; por isso a tabela de simulação mostra **141**, enquanto o total é **143**. Em 2026 o observado de 106 coincide nos dois recortes. Isso explica os totais distintos sem alterar o resultado do modelo.

No nulo beta-binomial de `09_extremos.py`, estimado a partir de vizinhança e heterogeneidade observada, a média simulada para 2026 foi 83,7 e a faixa central de 90% foi 72 a 95. Nenhuma das 400 réplicas alcançou 106; a fórmula com correção dá p = 1/401 ≈ 0,0025 para a cauda especificada. Em 2022, o modelo deu média 103,2, faixa de aproximadamente 88 a 118 e 0/400 réplicas atingindo as 141 observadas na amostra modelável. Isso é evidência de que os dados são extremos sob esse modelo particular, que também subestima os extremos de 2022; não é a probabilidade de fraude, nem prova que os dados estejam corretos. A comparação entre anos não exige presumir que 2022 foi íntegro. O modelo foi ajustado aos próprios dados, a análise dos zeros foi motivada após a observação e 400 simulações limitam a resolução.
