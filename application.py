from nursingHomeApp import create_app

application = create_app('nursingHomeApp.config_prod')
if __name__ == "__main__":
    application.run()
