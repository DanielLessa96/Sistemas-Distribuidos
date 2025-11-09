# 💬 Sistema de Chat P2P Descentralizado com Eleição de Líder (Python)

Este projeto implementa um sistema de mensagens instantâneas peer-to-peer (P2P) totalmente descentralizado, desenvolvido em Python.
O sistema é tolerante a falhas, mantendo a comunicação ativa mesmo quando um dos nós deixa a rede. Para isso, utiliza o Algoritmo do Bully, responsável por eleger automaticamente um novo coordenador sempre que o líder atual se torna inacessível.

Desenvolvido como Trabalho Final da disciplina de Sistemas Distribuídos, o sistema demonstra na prática conceitos fundamentais de coordenação distribuída, comunicação entre processos e resiliência de rede.

# ✨ Funcionalidades Principais

Arquitetura totalmente descentralizada: cada nó atua simultaneamente como cliente e servidor, sem necessidade de um ponto central de controle.

Descoberta automática de rede (Multicast UDP): novos nós localizam o coordenador ao escutar um endereço de multicast.

Gerenciamento de nós: o coordenador atribui identificadores únicos e informa a todos sobre entradas e saídas na rede.

Tolerância a falhas: o sistema detecta automaticamente a ausência do coordenador por meio de mensagens de heartbeat.

Eleição de líder (Algoritmo do Bully): ao identificar uma falha, os nós elegem o participante com o maior ID ativo como novo coordenador.

Histórico consistente: quando um novo nó entra, ele recebe o histórico completo do chat, garantindo que todas as mensagens fiquem sincronizadas entre os participantes.

Concorrência: a aplicação utiliza threads para executar múltiplas tarefas em paralelo, como escutar mensagens, processar comandos e verificar o estado dos peers.

# 🔧 Arquitetura e Comunicação

A comunicação entre os nós ocorre por meio de dois canais complementares:

# 🛰️ Multicast (UDP)

Usado para comunicação um-para-todos, eficiente e leve:

JOIN_REQUEST: enviado por novos nós para descobrir a rede, sendo respondido apenas pelo coordenador.

HEARTBEAT: mensagem periódica enviada pelo coordenador para indicar que está ativo.

# 🔗 Unicast (TCP)

Usado para comunicações ponto-a-ponto confiáveis:

JOIN_RESPONSE: resposta direta do coordenador com o ID, lista de peers e histórico de mensagens.

PEER_UPDATE: enviado a todos os nós quando há alterações na rede.

CHAT_MESSAGE: mensagens trocadas entre os participantes.

ELECTION, ELECTION_OK e COORDINATOR_ANNOUNCEMENT: mensagens usadas no processo de eleição do novo coordenador.

Mesmo durante o processo de eleição, o chat permanece operacional, garantindo continuidade da comunicação entre os nós ativos.

# 🧠 Conceitos Envolvidos

O sistema aplica e integra diversos princípios de Sistemas Distribuídos, incluindo:

Comunicação entre processos com UDP e TCP

Detecção de falhas e recuperação automática

Coordenação distribuída sem servidor central

Concorrência e sincronização entre threads

Implementação prática do Algoritmo do Bully

