import os
import sys
import multiprocessing
import streamlit.web.cli as stcli

def main():
    # Identifica a pasta onde os ficheiros foram descompactados temporariamente pelo PyInstaller
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    app_path = os.path.join(base_path, "app.py")

    # Passa os argumentos corretos para o Streamlit rodar localmente no executável
    sys.argv = [
        "streamlit", 
        "run", 
        app_path, 
        "--global.developmentMode=false",
        "--server.headless=false"  # Abre o navegador apenas uma vez ao iniciar
    ]
    
    sys.exit(stcli.main())

if __name__ == '__main__':
    # Esta linha é vital para impedir que o executável clone processos infinitamente
    multiprocessing.freeze_support()
    main()
