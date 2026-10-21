import sys, multiprocessing
multiprocessing.freeze_support()
if "--setup" in sys.argv:
    from yavis import config
    from yavis.setup_ollama import run_setup_gui
    run_setup_gui(config.load())
else:
    from yavis.app import main
    main()
