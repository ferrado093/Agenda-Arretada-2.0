# Agenda Arretada — App Android

1. Crie um repositório no github.com e envie TODO o conteúdo desta pasta
   (inclusive .github e assinatura).
2. Aba Actions -> "Gerar APK". Quando ficar verde, o arquivo aparece em
   Releases, com este link fixo (troque USUARIO e REPOSITORIO):
   https://github.com/USUARIO/REPOSITORIO/releases/latest/download/AgendaArretada.apk
3. Quem abrir o link no Android baixa o .apk e instala.

Cada novo envio gera uma nova versão com a mesma assinatura, então o app
atualiza por cima sem perder os compromissos.

## Ícone do app
O ícone é o arquivo assets/icone.png (PNG quadrado, 1024x1024). Para trocar,
substitua esse arquivo pela sua imagem, mantendo o mesmo nome, e envie ao GitHub.
Dica: deixe o desenho principal no centro, porque o Android corta as bordas
em alguns celulares. O fundo da imagem vira a cor de fundo do ícone.

## Novidades da versão 1.1
- **Grave sua voz**: aba "Personalidade e voz" > "Minhas vozes". Marque uma como padrão
  ou escolha uma voz diferente (ou nenhuma) em cada compromisso. A voz robótica foi removida.
- **Organizador**: pastas (processo, cliente, projeto) com peças/itens, status, prazo e
  anotações, e botão para criar o lembrete do prazo na agenda.
- O app agora pede permissão de microfone na primeira gravação.

## Novidades da versão 1.2
- **Alarme com a sua voz, mesmo com o app fechado**: no horário toca primeiro a voz gravada e,
  quando ela termina, o toque escolhido. Aparece em tela cheia por cima do bloqueio, com
  Concluir e Adiar 5 min (também na notificação).
- Escolha do toque, volume, volume crescente e quantas vezes o toque repete.
- Os alarmes voltam sozinhos depois que o celular reinicia.
- Botão "Testar alarme agora" e painel de permissões (notificações, tela cheia, bateria).
- Compromissos recorrentes: todo dia, dias úteis, toda semana, todo mês.
- O código nativo fica em tools/aplicar_nativo.py e é aplicado pelo GitHub Actions.

## Versão 1.2.1
- Campo "Seu nome": aparece na saudação e nos avisos (use {nome} nas suas frases).
