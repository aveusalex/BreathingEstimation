from funcoes import BreathEstimation, Apneia
import socket
import time
import threading
from picoscenes import Picoscenes


def processamento(estimador, apneia, pkts_recv):
    start = time.time()
    # calculando a diferença de fase
    phase_diff = estimador.diferenca_de_fase(estimador.get_csi())

    # filtrando com hampel
    estimador.hampel_jit(phase_diff, 10)

    # filtrando outliers pela tendência geral das subportadoras
    CSI_clean = estimador.outlier_channel_removal(phase_diff)
    del phase_diff

    # aplicando passa baixas
    CSI_filtered = estimador.passa_baixas(CSI_clean)
    del CSI_clean

    # aplicando PCA
    CSI_pca = estimador.pca(CSI_filtered)
    del CSI_filtered

    # buscando os picos da fft
    freq_resp_hz = estimador.busca_picos_fft(CSI_pca)
    del CSI_pca

    apneia.registra_estimativa(float(freq_resp_hz) * 90)
    ocorrencia = apneia.apneia()

    print("\033[97;42m\nRespiração estimada:\033[0m", float(freq_resp_hz) * 90)
    print(f"Tempo de execução {pkts_recv}:", time.time() - start)


def main():
    ip = "127.0.0.1"
    port = 1025
    # conectando ao udp
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind((ip, port))
    print("Conectado ao UDP")

    # instanciando o objeto de processamento
    estimador = BreathEstimation()
    apneia = Apneia(qtd_de_estimativas=20)
    pkts_recv = 0
    # recebendo os pacotes
    while True:
        pkt, _ = udp.recvfrom(8192)
        frames = Picoscenes(pkt)
        pkt = frames.raw[0]
        estimador.recebe_pacote_csi(pkt)
        pkts_recv += 1

        if pkts_recv >= estimador.fs * 20 and pkts_recv % estimador.fs == 0:
            # abrindo uma thread para não atrasar a captura de pacotes
            t = threading.Thread(target=processamento, args=(estimador, apneia, pkts_recv))
            t.start()


if __name__ == "__main__":
    main()
