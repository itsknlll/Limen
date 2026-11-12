-- Banco separado para os testes automatizados: os testes apagam e recriam o
-- esquema dele a cada execução, sem tocar nos dados do banco principal.
CREATE DATABASE limen_teste OWNER limen;
