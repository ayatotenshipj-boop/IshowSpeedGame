# Changelog

## v1.5.0 — A Grande Atualização
*"Finalmente chegou."*

### 🔥 Modo Infinito
O que vocês pediram muito. Agora tem um modo onde as waves não param nunca —
literalmente. Cada 10 waves um boss aparece e fica cada vez mais difícil.
Quanto mais longe você chegar, mais TexasCoins você ganha por kill.
Seu recorde vai pro leaderboard global na categoria Infinito, separado do
Normal e do Hard. Boa sorte passar da wave 30.

### 🃏 DrivingCar Speed — Primeira Carta Limitada
A primeira carta limitada do jogo chegou. É um buffer: ao ativar a skill,
ela acelera o SPA de todas as suas towers em +80% (e +120% no upgrade máximo).
Não acumula — uma DrivingCar ativa já resolve. Ela tem sistema de pity:
a cada 120 pulls sem tirar, a próxima é garantida. Vai aparecer na Store
com tudo certinho agora, não mais como placeholder vazio.

### 🗂️ Deck Builder
Agora você pode montar seu time antes da partida. Acesse pelo menu de
modos de jogo, veja quais cartas você tem, o que cada uma faz de verdade,
e escolha as que vão pro seu deck. Cartas que você não tem ficam bloqueadas
até você conseguir.

### 🎯 SetPriority — Prioridade de Alvo
Cada tower agora tem um seletor de alvo. Clica na tower e escolhe:
Primeiro, Último, Mais Forte ou Mais Fraco. Por padrão continua
mirando no primeiro — mas agora a escolha é sua.

### 🏆 Leaderboard com Categorias
O leaderboard agora tem três abas: Normal (speedrun), Hard (speedrun)
e Infinito (waves). Cada modo compete separado. Sem misturar.

### 🔧 Conquistas — Modo Infinito
Cinco novas conquistas pra quem encarar o Modo Infinito:
wave 10, 20, 30, 40 e 50. A da wave 50 vai levar um tempo.

### 🐛 Correções e ajustes
- Killthatboy, ShockedSpeed e Kindahomeless agora têm Full AOE
  fixo — afetam o campo inteiro sem depender de alcance
- Sistema de inventário e deck corrigido: quantidade não vai mais
  abaixo de zero, vender torre devolve a carta, deck inválido
  não derruba o jogo
- Pity da DrivingCarSpeed persiste entre sessões — fechar o jogo
  não zera seu progresso
- Leaderboard não trava mais o jogo se o Supabase estiver offline
- Spawn de inimigos agora usa delta time — sem aceleração estranha
  em máquinas mais rápidas
- Ancelotti não pode morrer duas vezes mais
- Buff de SPA revertido corretamente ao vender a DrivingCarSpeed
  durante a skill ativa

---
*Obrigado a quem jogou, reportou bug e ficou esperando essa atualização.*
