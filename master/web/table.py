'''
DataTable: a flask/sqlachemy module to generate HTML with server side data.

The project use datatable from http://www.datatables.net/
'''
__all__ = ('Table', 'Column')

import simplejson
from flask import url_for, request
from sqlalchemy import asc, desc

class Column(object):
    def __init__(self, name, field, display=None, formatter=None, width=None):
        super(Column, self).__init__()
        self.name = name
        self.field = field
        self.display = display
        self.formatter = formatter
        self.width = width

    def __html__(self):
        return '<th>%s</th>' % self.name

    def __js_def__(self, index, out):
        if self.width:
            out.append({'sWidth': self.width, 'aTargets': [index]})

    def get_field(self, entry):
        if self.display:
            value = self.display(entry)
        else:
            value = getattr(entry, self.field)
        if self.formatter:
            return self.formatter(value)
        return value

class Table(object):
    __uniqid = 0
    db_table = None
    db_session  = None
    display_length = 20
    activate_sort = True
    activate_info = True
    activate_paginate = True
    activate_scroll_infinite = False
    activate_filter = True
    activate_length_change = True
    activate_scroll_collapse = True
    pagination_type = 'full_numbers'
    scroll_x = ''
    scroll_y = ''
    href_link = None

    def __init__(self, **kwargs):
        super(Table, self).__init__()
        self.html_id = kwargs.get('html_id', None)
        if self.html_id is None:
            Table.__uniqid += 1
            self.html_id = 'datatable%d' % Table.__uniqid

    def query(self):
        return self.db_session.query(self.db_table)

    def ajax(self):
        q = self.query()

        # total number of entries
        count = q.count()

        # search
        if 'sSearch' in request.args:
            search = None
            for col in self.columns:
                field = getattr(self.db_table, col.field)
                field = field.like('%%%s%%' % request.args['sSearch'])
                if search is None:
                    search = field
                else:
                    search = search | field
            q = q.filter(search)

        # sorting
        if 'iSortingCols' in request.args:
            field = self.columns[int(request.args['iSortCol_0'])].field
            db_field = getattr(self.db_table, field)
            if request.args['sSortDir_0'] == 'asc':
                db_field = asc(db_field)
            else:
                db_field = desc(db_field)
            q = q.order_by(db_field)

        # get the number after filter
        count_filtered = q.count()

        # pagination
        if self.activate_scroll_infinite:
            limit = self.display_length
        else:
            limit = request.args['iDisplayLength']
        offset = request.args['iDisplayStart']
        entries = q.offset(offset).limit(limit)

        # construct the output
        data = []
        columns = self.columns
        for entry in entries:
            data.append([col.get_field(entry) for col in columns])

        return simplejson.dumps({
            'sEcho': request.args['sEcho'],
            'iTotalRecords': count,
            'iTotalDisplayRecords': count_filtered,
            'aaData': data
        })

    def __json_columns_defs__(self):
        out = []
        for index, col in enumerate(self.columns):
            col.__js_def__(index, out)
        return simplejson.dumps(out)

    def __js_rowclick__(self):
        return ''

    def __html_columns__(self):
        out = ['<tr>']
        for col in self.columns:
            out.append(col.__html__())
        out.append('</tr>')
        return ''.join(out)

    def __html__(self):
        data = {
            'html_id': self.html_id,
            'columns': self.__html_columns__(),
            'click_callback': self.__js_rowclick__(),

            # datatable
            'iDisplayLength': str(int(self.display_length)),
            'bSort': str(bool(self.activate_sort)).lower(),
            'bInfo': str(bool(self.activate_info)).lower(),
            'bPaginate': str(bool(self.activate_paginate)).lower(),
            'bScrollInfinite': str(bool(self.activate_scroll_infinite)).lower(),
            'bScrollCollapse': str(bool(self.activate_scroll_collapse)).lower(),
            'bFilter': str(bool(self.activate_filter)).lower(),
            'bLengthChange': str(bool(self.activate_length_change)).lower(),
            'sScrollX': str(self.scroll_x),
            'sScrollY': str(self.scroll_y),
            'sPaginationType': str(self.pagination_type),
            'sAjaxSource': url_for(self.source),
            'aoColumnDefs': self.__json_columns_defs__()
        }

        html = '''
        <script type="text/javascript">
        $(document).ready(function() {
            $("#%(html_id)s").dataTable({
                'bJQueryUI': true,
                'bProcessing': true,
                'bServerSide': true,
                'bScrollInfinite': %(bScrollInfinite)s,
                'bScrollCollapse': %(bScrollCollapse)s,
                'bSort': %(bSort)s,
                'bInfo': %(bInfo)s,
                'bFilter': %(bFilter)s,
                'bLengthChange': %(bLengthChange)s,
                'bPaginate': %(bPaginate)s,
                'iDisplayLength': %(iDisplayLength)s,
                'sAjaxSource': '%(sAjaxSource)s',
                'sPaginationType': '%(sPaginationType)s',
                'sScrollY': '%(sScrollY)s',
                'sScrollX': '%(sScrollX)s',
                'aoColumnDefs': %(aoColumnDefs)s
            });
        });
        $("#%(html_id)s tbody tr").live('click', function() {
            %(click_callback)s
        });
        </script>
        <table id="%(html_id)s">
            <thead>
                %(columns)s
            </thead>
            <tbody>
            </tbody>
        </table>
        ''' % data
        return html
