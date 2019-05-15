import logging
from app import create_app_api,APP_URL_PREFIX
from app.utils.code_msg import CommonJsonRet
from app.digiccy_log import init_log

from flask_zipkin import Zipkin

# 日志
init_log()

# app
app, api = create_app_api()


zipkin = Zipkin(sample_rate=int(app.config["CONFIG_ZIPKIN_SAMPLERATE"]))
zipkin.init_app(app)


# 统一404处理
@app.errorhandler(404)
def page_not_not_found(error):
    return CommonJsonRet(code=404,
                           success=False,
                           msg="404 Not Found . there is not this api",
                           data="").to_json_str()


# 统一异常处理
@api.errorhandler
def default_error_handler(exception):
    # 异常栈写入
    logging.error(exception)
    return CommonJsonRet(code=500,
                           success=False,
                           msg=exception.message,
                           data="server exception capture").to_json()


@zipkin.exempt
@app.route(APP_URL_PREFIX + "/health_check")
def health_check():
    return CommonJsonRet(code=200,
                           success=True,
                           msg="health check is ok",
                           data="").to_json_str()


if __name__ == '__main__':
    print(app.config)
    # from app import db
    # from app.models import Config
    # s = Config(
    #     key='digiccy.ETH.base.account',
    #     value='0x382085035c9c8537399221b41a9edda4a5bd1fea2bf3b16f4dd3a17df66204ee',
    # )
    # db.session.add(s)
    # db.session.commit()
    app.run(debug=True, host='0.0.0.0', port=58483)
