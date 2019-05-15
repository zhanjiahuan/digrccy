import logging

from flask_restplus import Namespace, Resource

from app.models import *
from app.utils.cover_resource import CoverRequestParser
from app.utils.code_msg import CodeMsg, create_response

base_ns = Namespace("base", description="base API")




# @base_ns.route('/task')
# class TaskSwitch(Resource):
#     @base_ns.doc(
#         params={
#             'status': '状态1=开启0=关闭'
#         },
#         description=u'定时任务开关'
#     )
#     def post(self):
#         parser_ = CoverRequestParser()
#         parser_.add_argument("status", type=str, required=True)
#         params = parser_.parse_args()
#         status = params['status']
#
#         if status not in ('1', '0'):
#             return create_response(CodeMsg.CM(1051, 'status错误'))
#
#         tasks_conf = Config.query.filter_by(key='task.switch').first()
#         tasks_conf.value = status
#         try:
#             db.session.add(tasks_conf)
#             db.session.commit()
#         except Exception as e:
#             logging.error(e)
#             return create_response(CodeMsg.CM(1050,'操作失败'))
#         return create_response(CodeMsg.SUCCESS)