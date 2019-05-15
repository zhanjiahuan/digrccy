import flask
import six

from flask import request
from werkzeug import exceptions
from werkzeug.exceptions import HTTPException
from flask_restplus.reqparse import ParseResult,Argument
from flask_restplus import reqparse


def cover_abort(codes=500, message=None, **kwargs):
    try:
        flask.abort(codes)
    except HTTPException as e:
        if message:
            kwargs['message'] = str(message)
        if kwargs:
            e.data = kwargs
        raise


class CoverArgument(Argument):
    def handle_validation_error(self, error, bundle_errors):
        error_str = six.text_type(error)
        error_msg = ' '.join([six.text_type(self.help), error_str]) if self.help else error_str
        errors = {self.name: error_msg}

        if bundle_errors:
            return ValueError(error), errors
        cover_abort(400, None,
                    code=400,
                    success=False,
                    msg=errors,
                    data="")


class CoverRequestParser(reqparse.RequestParser):
    def __init__(self):
        super(CoverRequestParser, self).__init__(argument_class=CoverArgument, result_class=ParseResult,
                 trim=False, bundle_errors=False)

    def parse_args(self, req=None, strict=False):
        if req is None:
            req = request

        result = self.result_class()

        req.unparsed_arguments = dict(self.argument_class('').source(req)) if strict else {}
        errors = {}
        for arg in self.args:
            value, found = arg.parse(req, self.bundle_errors)
            if isinstance(value, ValueError):
                errors.update(found)
                found = None
            if found or arg.store_missing:
                result[arg.dest or arg.name] = value
        if errors:
            cover_abort(400, None,
                        code=400,
                        success=False,
                        msg=errors,
                        data="")

        if strict and req.unparsed_arguments:
            arguments = ', '.join(req.unparsed_arguments.keys())
            msg = 'Unknown arguments: {0}'.format(arguments)
            raise exceptions.BadRequest(msg)
        return result