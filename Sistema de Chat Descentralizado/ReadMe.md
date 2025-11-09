🚀 Sistema de Chat P2P Descentralizado com Eleição de Líder (Python)
Implementação de um sistema de mensagens instantâneas (chat) P2P (peer-to-peer) totalmente descentralizado, desenvolvido em Python. O sistema é resiliente a falhas de nós e utiliza o Algoritmo do Bully para a eleição automática de um novo coordenador.

Este projeto foi desenvolvido como Trabalho Final para a disciplina de Sistemas Distribuídos.

✨ Funcionalidades Principais

Arquitetura 100% P2P: Sem necessidade de um servidor central; cada nó atua como cliente e servidor.


Descoberta de Rede (Multicast): Novos nós entram na rede "sintonizando" um endereço de multicast (UDP) para encontrar o coordenador.


Gerenciamento de Nós: Um nó é eleito como Coordenador para centralizar tarefas de gerenciamento, como atribuir IDs únicos e anunciar saídas.



Tolerância a Falhas: O sistema detecta automaticamente a falha do nó coordenador através de um mecanismo de heartbeats.



Eleição de Líder (Algoritmo do Bully): Quando o coordenador falha, os nós restantes iniciam uma eleição para escolher o nó ativo com o ID mais alto como o novo líder.


Histórico Consistente: Novos nós recebem o histórico completo do chat ao entrar, e todas as mensagens são replicadas para todos os participantes.

Concorrência: O sistema utiliza threading para lidar com múltiplas tarefas simultâneas (ouvir a rede, receber inputs do usuário, verificar heartbeats).

🔧 Como Funciona: Arquitetura
O sistema utiliza dois canais de comunicação principais:

Multicast (UDP): Usado para comunicação "um-para-todos" de baixo custo.

JOIN_REQUEST: Enviado por um novo nó para descobrir a rede. Apenas o coordenador responde.


HEARTBEAT: Enviado periodicamente pelo coordenador para provar que está ativo.

Unicast (TCP): Usado para comunicação "ponto-a-ponto" confiável.

JOIN_RESPONSE: Resposta direta do coordenador para o novo nó (com ID, lista de peers, histórico).

PEER_UPDATE: Enviado pelo coordenador para todos os nós quando alguém entra ou sai.

CHAT_MESSAGE: Mensagem de chat enviada de um nó para todos os outros peers.

ELECTION, ELECTION_OK, COORDINATOR_ANNOUNCEMENT: Mensagens usadas durante o processo de eleição do Algoritmo do Bully.




O chat continuará funcionando normalmente sob a nova liderança.
