import socket
import threading
import time
import json
import struct
import random

# --- Configurações da Rede ---
# Use um IP de multicast na faixa 224.0.0.0 a 239.255.255.255
MULTICAST_GROUP = '224.1.1.1'
MULTICAST_PORT = 5007
TCP_PORT_BASE = 10000  # Porta base para conexões TCP

# --- Constantes do Protocolo ---
HEARTBEAT_INTERVAL = 5  # Segundos entre heartbeats do coordenador
HEARTBEAT_TIMEOUT = 15  # Segundos para considerar o coordenador inativo
ELECTION_TIMEOUT = 5    # Segundos para aguardar respostas em uma eleição

class ChatNode:
    """
    Representa um nó no sistema de chat descentralizado.
    Cada nó pode atuar como um participante normal ou como o coordenador da rede.
    """

    def __init__(self, nickname):
        """
        Construtor da classe. Inicializa o estado do nó e configura os sockets.
        """
        self.nickname = nickname
        self.node_id = -1  # ID único na rede, atribuído pelo coordenador
        self.tcp_port = TCP_PORT_BASE + random.randint(100, 999) # Porta TCP para este nó
        self.peers = {}  # Dicionário de peers: {node_id: (ip, port, nickname)}
        self.coordinator_id = -1
        self.is_coordinator = False
        self.is_in_election = False
        self.last_heartbeat_time = time.time()
        self.chat_history = []

        # Inicialização dos Sockets
        self.tcp_server_socket = self._setup_tcp_server()
        self.multicast_socket = self._setup_multicast_socket()

        print(f"[{self.nickname}] Nó iniciado. Ouvindo em TCP na porta {self.tcp_port}.")

    def _setup_tcp_server(self):
        """  Cria e configura o socket TCP principal do nó.
        Este socket fica ouvindo por conexões diretas (chat, eleição, etc.)."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('', self.tcp_port))
        server.listen(10)
        return server

    def _setup_multicast_socket(self):
        """Cria e configura o socket UDP para comunicação multicast.
        Este socket "sintoniza" o canal de descoberta e heartbeats."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', MULTICAST_PORT))
        
        # Adiciona o socket ao grupo de multicast
        mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        return sock

    def start(self):
        """Inicia todas as threads de operação do nó."""
        threading.Thread(target=self.listen_tcp, daemon=True).start()
        threading.Thread(target=self.listen_multicast, daemon=True).start()
        threading.Thread(target=self.check_coordinator_health, daemon=True).start()
        
        # Tenta se juntar a uma rede existente
        self.join_network()
        
        # Loop principal para entrada do usuário
        self.user_input_loop()

    def join_network(self):
        """Envia uma mensagem de descoberta via multicast para encontrar o coordenador."""
        print("[System] Procurando por uma rede existente...")
        message = self.create_message("JOIN_REQUEST", {"port": self.tcp_port, "nickname": self.nickname})
        self.multicast_socket.sendto(message.encode(), (MULTICAST_GROUP, MULTICAST_PORT))
        
        # Se não houver resposta, torna-se o primeiro nó e coordenador
        time.sleep(ELECTION_TIMEOUT) # Espera por uma resposta
        if self.node_id == -1:
            print("[System] Nenhuma rede encontrada. Tornando-se o primeiro nó e coordenador.")
            self.become_coordinator(is_first_node=True)

    def become_coordinator(self, is_first_node=False):
        """Assume o papel de coordenador."""
        self.is_coordinator = True
        self.is_in_election = False
        
        if is_first_node:
            self.node_id = 1
            self.coordinator_id = 1
            self.peers[self.node_id] = ('127.0.0.1', self.tcp_port, self.nickname)
        else:
            self.coordinator_id = self.node_id

        print(f"*** Eu (ID: {self.node_id}) sou o novo coordenador! ***")
        
        # Inicia o envio de heartbeats
        threading.Thread(target=self.send_heartbeats, daemon=True).start()
        
        # Anuncia para todos que é o novo coordenador (em caso de eleição)
        if not is_first_node:
            msg = self.create_message("COORDINATOR_ANNOUNCEMENT", {"coordinator_id": self.node_id})
            self.broadcast_tcp(msg)


    def listen_tcp(self):
        """Ouve por conexões TCP de outros nós."""
        while True:
            conn, addr = self.tcp_server_socket.accept()
            threading.Thread(target=self.handle_tcp_connection, args=(conn, addr), daemon=True).start()

    def handle_tcp_connection(self, conn, addr):
        """Processa mensagens recebidas via TCP."""
        try:
            data = conn.recv(4096).decode()
            if data:
                message = json.loads(data)
                msg_type = message.get("type")
                payload = message.get("payload")
                
                # Resposta de um coordenador a um pedido de entrada
                if msg_type == "JOIN_RESPONSE":
                    self.node_id = payload["new_id"]
                    self.peers = {int(k): tuple(v) for k, v in payload["peers"].items()}
                    self.coordinator_id = payload["coordinator_id"]
                    self.chat_history = payload["history"]
                    self.last_heartbeat_time = time.time()
                    print(f"[System] Conectado à rede com sucesso! Meu ID é {self.node_id}.")
                    print(f"[System] Coordenador atual: ID {self.coordinator_id}.")
                    print(f"[System] Nós na rede: {list(self.peers.keys())}")
                    self.display_history()

                # Atualização da lista de peers (novo nó ou saída)
                elif msg_type == "PEER_UPDATE":
                    self.peers = {int(k): tuple(v) for k, v in payload["peers"].items()}
                    if "joined" in payload:
                        print(f"[System] Nó {payload['joined']} ('{payload['nickname']}') entrou no chat.")
                    elif "departed" in payload:
                        print(f"[System] Nó {payload['departed']} saiu do chat.")
                    print(f"[System] Nós na rede: {list(self.peers.keys())}")
                
                # Mensagem de chat
                elif msg_type == "CHAT_MESSAGE":
                    sender_id = payload['sender_id']
                    sender_nickname = self.peers.get(sender_id, [None, None, 'Desconhecido'])[2]
                    chat_msg = f"[{sender_nickname} (ID:{sender_id})]: {payload['text']}"
                    self.chat_history.append(chat_msg)
                    print(chat_msg)

                # --- Lógica do Algoritmo do Bully ---
                elif msg_type == "ELECTION":
                    sender_id = payload['sender_id']
                    print(f"[Election] Recebi uma mensagem de eleição do nó {sender_id}.")
                    if self.node_id > sender_id:
                        # Responde que está vivo e tem ID maior
                        response = self.create_message("ELECTION_OK", {"sender_id": self.node_id})
                        self.send_tcp_message(sender_id, response)
                        # Inicia sua própria eleição se não estiver em uma
                        if not self.is_in_election:
                            self.start_election()
                
                elif msg_type == "ELECTION_OK":
                    # Alguém com ID maior respondeu, então não serei o coordenador
                    print(f"[Election] Recebi um OK do nó {payload['sender_id']}. Vou parar minha candidatura.")
                    self.is_in_election = False # Cancela a eleição

                elif msg_type == "COORDINATOR_ANNOUNCEMENT":
                    new_coordinator_id = payload['coordinator_id']
                    self.coordinator_id = new_coordinator_id
                    self.is_coordinator = (self.node_id == new_coordinator_id)
                    self.is_in_election = False
                    self.last_heartbeat_time = time.time()
                    print(f"[System] Novo coordenador eleito: Nó {new_coordinator_id}.")
        
        except (json.JSONDecodeError, ConnectionResetError, OSError):
            pass # Ignora erros de conexão ou de mensagem malformada
        finally:
            conn.close()

    def listen_multicast(self):
        """Ouve por mensagens multicast (descoberta e heartbeats)."""
        while True:
            data, addr = self.multicast_socket.recvfrom(1024)
            message = json.loads(data.decode())
            msg_type = message.get("type")
            payload = message.get("payload")
            
            # Coordenador recebe pedido de entrada
            if self.is_coordinator and msg_type == "JOIN_REQUEST":
                new_node_port = payload["port"]
                new_node_nickname = payload["nickname"]
                new_node_addr = (addr[0], new_node_port)
                
                # Gera um novo ID único
                new_id = max(self.peers.keys()) + 1 if self.peers else 1
                
                # Adiciona novo nó à lista de peers
                self.peers[new_id] = (new_node_addr[0], new_node_addr[1], new_node_nickname)
                print(f"[Coordinator] Novo nó '{new_node_nickname}'@{new_node_addr} solicitou entrada. Atribuindo ID {new_id}.")
                
                # Envia resposta ao novo nó com seu ID e a lista de peers
                response = self.create_message("JOIN_RESPONSE", {
                    "new_id": new_id,
                    "peers": self.peers,
                    "coordinator_id": self.coordinator_id,
                    "history": self.chat_history
                })
                self.send_tcp_message_by_addr(new_node_addr, response)
                
                # Anuncia o novo nó para os demais
                update_msg = self.create_message("PEER_UPDATE", {"peers": self.peers, "joined": new_id, "nickname": new_node_nickname})
                self.broadcast_tcp(update_msg, exclude_ids=[new_id])

            # Qualquer nó (exceto o coordenador) recebe um heartbeat
            elif not self.is_coordinator and msg_type == "HEARTBEAT":
                self.coordinator_id = payload['coordinator_id']
                self.last_heartbeat_time = time.time()
               
    
    def send_heartbeats(self):
        """(Apenas Coordenador) Envia heartbeats via multicast periodicamente."""
        while self.is_coordinator:
            message = self.create_message("HEARTBEAT", {"coordinator_id": self.node_id})
            self.multicast_socket.sendto(message.encode(), (MULTICAST_GROUP, MULTICAST_PORT))
            time.sleep(HEARTBEAT_INTERVAL)

    def check_coordinator_health(self):
        """Verifica periodicamente a saúde do coordenador."""
        while True:
            time.sleep(HEARTBEAT_TIMEOUT)
            # Não inicia eleição se for o coordenador, se não estiver na rede ou se já estiver em uma eleição
            if not self.is_coordinator and self.node_id != -1 and not self.is_in_election:
                if time.time() - self.last_heartbeat_time > HEARTBEAT_TIMEOUT:
                    print("[System] Coordenador não responde. Iniciando eleição...")
                    self.start_election()
                    
    def start_election(self):
        """Inicia o processo de eleição (Algoritmo do Bully)."""
        self.is_in_election = True
        
        higher_id_peers = [pid for pid in self.peers if pid > self.node_id]
        
        if not higher_id_peers:
            # Se não há ninguém com ID maior, este nó se torna o coordenador
            self.become_coordinator()
            return
            
        # Envia mensagem de eleição para todos os nós com ID maior
        print(f"[Election] Enviando mensagem de eleição para os nós: {higher_id_peers}")
        for pid in higher_id_peers:
            msg = self.create_message("ELECTION", {"sender_id": self.node_id})
            self.send_tcp_message(pid, msg)

        # Espera por uma resposta "OK". Se não receber, se torna o coordenador.
        time.sleep(ELECTION_TIMEOUT)
        if self.is_in_election: # Se ninguém com ID maior respondeu (flag não foi zerada)
            print("[Election] Nenhum nó com ID maior respondeu. Assumindo como coordenador.")
            self.become_coordinator()

    def user_input_loop(self):
        """Loop para capturar e enviar mensagens de chat do usuário."""
        while self.node_id == -1:
            time.sleep(1) # Aguarda até que o nó seja registrado na rede
        
        print("\n--- Chat iniciado. Digite suas mensagens e pressione Enter. Digite 'exit' para sair. ---")

        while True:
            try:
                text = input()
                if text.lower() == 'exit':
                    self.leave_network()
                    break
                
                chat_message = self.create_message("CHAT_MESSAGE", {
                    "sender_id": self.node_id,
                    "text": text
                })
                # Adiciona a *minha própria* mensagem ao meu histórico 
                my_chat_msg = f"[Você (ID:{self.node_id})]: {text}"
                self.chat_history.append(my_chat_msg)
                
                self.broadcast_tcp(chat_message)
            except (KeyboardInterrupt, EOFError):
                self.leave_network()
                break

    def leave_network(self):
        """Notifica o coordenador sobre a saída e encerra o nó."""
        print("[System] Saindo da rede...")
        if self.is_coordinator and len(self.peers) > 1:
            # Se for o coordenador e houver outros nós, aciona uma eleição nos outros
            # Uma forma simples é apenas parar de enviar heartbeats
            print("[Coordinator] Encerrando. Outros nós irão eleger um novo líder.")
        elif self.node_id != -1 and self.coordinator_id in self.peers:
            # Se for um nó normal, avisa o coordenador
            msg = self.create_message("LEAVE_REQUEST", {"node_id": self.node_id})
            self.send_tcp_message(self.coordinator_id, msg) 

        self.tcp_server_socket.close()
        self.multicast_socket.close()
        import os
        os._exit(0)

    # --- Funções Utilitárias de Comunicação ---

    def create_message(self, msg_type, payload):
        """Cria uma mensagem JSON padronizada."""
        return json.dumps({"type": msg_type, "payload": payload})

    def send_tcp_message(self, target_id, message):
        """Envia uma mensagem TCP para um nó específico pelo seu ID."""
        if target_id in self.peers:
            target_addr = (self.peers[target_id][0], self.peers[target_id][1])
            self.send_tcp_message_by_addr(target_addr, message)

    def send_tcp_message_by_addr(self, target_addr, message):
        """Envia uma mensagem TCP para um endereço (IP, porta) específico."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(target_addr)
                sock.sendall(message.encode())
        except (ConnectionRefusedError, OSError):
            # Se a conexão for recusada, o nó provavelmente caiu.
            # A detecção de falha cuidará de removê-lo eventualmente.
            pass

    def broadcast_tcp(self, message, exclude_ids=None):
        """Envia uma mensagem TCP para TODOS os peers na lista."""
        if exclude_ids is None:
            exclude_ids = []
        
        # O ID do próprio nó é sempre excluído
        exclude_ids.append(self.node_id)
        
        for peer_id in self.peers:
            if peer_id not in exclude_ids:
                self.send_tcp_message(peer_id, message)

    def display_history(self):
        """Exibe o histórico de chat recebido ao entrar na rede."""
        print("\n--- Histórico de Mensagens Recebido ---")
        for msg in self.chat_history:
            print(msg)
        print("-------------------------------------\n")


if __name__ == "__main__":
    try:
        user_nickname = input("Digite seu nickname: ")
        if not user_nickname:
            # Gera um nickname padrão se o usuário não digitar nada   
            user_nickname = f"User_{random.randint(100, 999)}"
        # Cria a instância do nó      
        node = ChatNode(nickname=user_nickname)
        node.start()
    except Exception as e:
        print(f"Ocorreu um erro fatal: {e}")