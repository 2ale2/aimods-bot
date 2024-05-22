import logging

# creo logger
db_logger = logging.getLogger("dblogger")
# imposto livello minimo
db_logger.setLevel(logging.INFO)

# creo formatter e file handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler("../misc/logs/database.log")

# indico formato a file handler
file_handler.setFormatter(formatter)

# aggiungo handler al logger
db_logger.addHandler(file_handler)
