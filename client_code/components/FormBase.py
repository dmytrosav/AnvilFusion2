# Base generic data input form control
import anvil.js
from anvil.js.window import jQuery, ej
from . import FormInputs
from .MultiFieldInput import MultiFieldInput, HyperlinkInput
from SubformGrid import SubformGrid
from ..tools.utils import AppEnv, camel_to_snake, camel_to_title, new_el_id
import string

POPUP_DEFAULT_TARGET = 'body'
POPUP_WIDTH_COL1 = '400px'
POPUP_WIDTH_COL2 = '500px'
POPUP_WIDTH_COL3 = '600px'

DIALOG_FULLSCREEN_HEIGHT_OFFSET = 12


# Helper function to update form submit behavior on Enter key click
def form_submit(args):
    if args.key == 'Enter':
        anvil.js.window.document.activeElement.dispatchEvent(anvil.js.window.Event('change'))
        args.preventDefault()


# Basic class to build a popup form dialog
class FormBase:
    def __init__(self,
                 target=None,
                 modal=False,
                 model='Base',
                 header=None,
                 fields=None,
                 sections=None,
                 tabs=None,
                 buttons=None,
                 button_save_label='Save',
                 button_cancel_label='Cancel',
                 subforms=None,
                 content=None,
                 action='add',
                 data=None,
                 persist=True,
                 update_source=None,
                 source=None,
                 width=POPUP_WIDTH_COL1,
                 height='auto',
                 validation=None
                 ):
        print('Base Form', model)

        self.form_model = model
        self.class_name = getattr(AppEnv.data_models, self.form_model, None)
        self.form_fields = fields
        self.subforms = subforms if subforms is not None else []
        self.persist = persist
        self.update_source = update_source
        self.source = source
        self.form_tabs = None
        self.fullscreen = False
        self.modal = modal

        self.target = target
        self.target_el = anvil.js.call('$', f"#{target}" if target is not None else POPUP_DEFAULT_TARGET)[0]
        self.container_uid = new_el_id()
        self.container_el = anvil.js.window.document.createElement('div')
        self.container_el.setAttribute('id', self.container_uid)
        self.container_el.style.visibility = 'hidden'
        self.target_el.append(self.container_el)
        self.form_name = f"form_{camel_to_snake(self.form_model)}"
        self.form_uid = new_el_id()
        self.form_id = f"{AppEnv.APP_ID}_{self.form_uid}_{self.form_name}"
        self.form_el = None
        self.action = action
        self.data = data
        self.validation = validation
        self.validator = None

        # create form HTML content
        if content is not None:
            self.form_content = f'<form id="{self.form_id}">{content}</form>'

        elif tabs is not None:
            self.form_content, self.form_fields, self.form_tabs = self.tabs_content(tabs)

        elif sections is not None:
            self.form_content, self.form_fields = self.sections_content(sections)

        else:
            # create the list of form fields from the list of model attributes if fields are not defined
            if self.form_fields is None:
                self.form_fields = self.model_fields(self.class_name)
            self.form_content = self.fields_content(self.form_fields)

        self.form_content = f'<form id="{self.form_id}" style="padding-top:1em;!important">' + self.form_content + '</form>'
        self.default_data = {field.name: field.value for field in self.form_fields}
        if not self.data:
            print('no data')
            instance_data = {x: self.default_data[x] for x in self.default_data
                             if x in self.class_name._attributes or x in self.class_name._relationships}
            self.data = self.class_name(**instance_data)

        # create form control
        self.form = ej.popups.Dialog({
            'header': header or string.capwords(self.action + ' ' + camel_to_title(self.form_model)),
            'content': self.form_content,
            'showCloseIcon': True,
            'buttons': buttons or [
                {
                    'buttonModel':
                        {'isPrimary': True, 'content': button_save_label, 'cssClass': 'da-save-button'},
                    'click': self.form_save,
                },
                {
                    'buttonModel':
                        {'isPrimary': False, 'content': button_cancel_label, 'cssClass': 'da-cancel-button'},
                    'click': self.form_cancel,
                },
            ],
            'target': self.target_el,
            'isModal': self.modal,
            'width': width,
            'height': '100%' if self.fullscreen is True else height,
            'visible': False,
            'position': {'X': 'center', 'Y': '100'},
            'animationSettings': {'effect': 'Zoom'},
            'cssClass': 'e-fixed py-dialog',
            'open': self.form_open,
            'close': self.form_cancel,
            'beforeOpen': self.before_open,
            'created': self.form_created,
        })
        self.form.cssClass = 'e-fixed py-dialog'
        self.form.appendTo(self.container_el)

        if self.form_tabs is not None:
            self.tabs = ej.navigations.Tab({'items': self.form_tabs, })
            self.tabs.appendTo(jQuery(f"#{self.form_id}_tabs")[0])

    def tabs_content(self, tabs):
        html_content = f'<div id="{self.form_id}_tabs"></div>'
        tab_items = []
        form_fields = []
        for tab in tabs:
            tab_id = f"{self.form_id}_tab_{tab['name']}"
            tab_items.append({'header': {'text': tab['label']}, 'content': f"#{tab_id}"})
            html_content += f'<div id="{tab_id}">'
            if 'sections' in tab:
                tab_html, tab_fields = self.sections_content(tab['sections'])
                html_content += f'<br>{tab_html}'
                form_fields.extend(tab_fields)
            elif 'fields' in tab:
                html_content += self.fields_content(tab['fields'])
                form_fields.extend(tab['fields'])
            html_content += '</div>'
        return html_content, form_fields, tab_items

    @staticmethod
    def model_fields(model_class):
        form_fields = []
        if model_class is not None:
            print('class ', model_class)
            for attr_name, attr_class in model_class._attributes.items():
                if attr_class.field_type.InputType == 'MultiFieldInput':
                    form_fields.append(MultiFieldInput(name=attr_name,
                                                       label=string.capwords(attr_name.replace("_", " ")),
                                                       model=model_class, ))
                elif attr_class.field_type.InputType == 'HyperlinkInput':
                    form_fields.append(HyperlinkInput(name=attr_name,
                                                      label=string.capwords(attr_name.replace("_", " ")), ))
                elif attr_class.field_type.InputType == 'SubformGrid':
                    form_fields.append(SubformGrid(name=attr_name,
                                                   label=string.capwords(attr_name.replace("_", " ")),
                                                   schema=attr_class.schema, ))
                # if attr_class.field_type.InputType not in ('MultiFieldInput', 'SubformGrid'):
                else:
                    attr_input = getattr(FormInputs, attr_class.field_type.InputType)
                    form_fields.append(attr_input(name=attr_name, label=string.capwords(attr_name.replace("_", " "))))
            for ref_name in model_class._relationships.keys():
                ref_class = model_class._relationships[ref_name].__dict__['class_name']
                ref_class = getattr(AppEnv.data_models, ref_class, None)
                # ref_title = [*ref_class._attributes.keys()][0]
                ref_title = ref_class._title
                form_fields.append(
                    FormInputs.LookupInput(
                        model=ref_class.__name__,
                        name=ref_name,
                        label=string.capwords(ref_name.replace("_", " ")),
                        id_field='uid',
                        text_field=ref_title,
                        # data=[*ref_class.search()]
                    )
                )
            # for attr_name, attr_class in model_class._attributes.items():
            #     if attr_class.field_type.InputType == 'MultiFieldInput':
            #         form_fields.append(MultiFieldInput(name=attr_name,
            #                                            label=string.capwords(attr_name.replace("_", " ")),
            #                                            model=model_class, ))
            # for attr_name, attr_class in model_class._attributes.items():
            #     if attr_class.field_type.InputType == 'SubformGrid':
            #         form_fields.append(SubformGrid(name=attr_name,
            #                                        label=string.capwords(attr_name.replace("_", " ")),
            #                                        schema=attr_class.schema, ))
        return form_fields

    @staticmethod
    def fields_content(fields):
        html_content = ''
        for field in fields:
            if field is None or isinstance(field, str):
                html_content += f'<div class="row"><div class="col-xs-12" id="{field}"></div></div>'
            else:
                html_content += f'<div class="row"><div class="col-xs-12" id="{field.container_id}"></div></div>'
        return html_content

    @staticmethod
    def sections_content(sections):
        html_content = ''
        form_fields = []
        for section in sections:
            section['id'] = new_el_id()
            html_content += f'<div class="row" id="{section["id"]}"><div class="col-xs-12">'
            if 'label' in section and section['label'] is not None:
                html_content += (f'<h5 class="{section.get("label_class", "pm-dialog-section-header")}" '
                                 f'style={section.get("label_style", "")}>{section["label"]}</h5>')
            if 'rows' in section:
                for row in section['rows']:
                    html_content += '<div class="row">'
                    col_size = 12 // len(row)
                    for field in row:
                        # print('field', field)
                        if field is None or isinstance(field, str):
                            html_content += f'<div class="col-xs-{col_size}">{field or ""}</div>'
                        else:
                            form_fields.append(field)
                            html_content += f'<div class="col-xs-{col_size}" id="{field.container_id}"></div>'
                    html_content += '</div>'
            elif 'cols' in section:
                col_size = 12 // len(section['cols'])
                html_content += '<div class="row">'
                for col in section['cols']:
                    html_content += f'<div class="col-xs-{col_size}">'
                    for field in col:
                        if field is None or isinstance(field, str):
                            html_content += f'<div class="col-xs-{col_size}">{field}</div>'
                        else:
                            form_fields.append(field)
                            html_content += f'<div id="{field.container_id}"></div>'
                    html_content += '</div>'
                html_content += '</div>'
            html_content += '</div></div>'
        return html_content, form_fields

    def form_show(self, fullscreen=None):
        print('action: form show')
        view_mode = fullscreen if fullscreen is not None else self.fullscreen
        self.form.show(view_mode)
        if view_mode:
            container_el_height = int(self.container_el.style['max-height'][0:-2]) - DIALOG_FULLSCREEN_HEIGHT_OFFSET
            self.container_el.style.top = f"{DIALOG_FULLSCREEN_HEIGHT_OFFSET}px"
            self.container_el.style['max-height'] = f"{container_el_height}px"

    def form_created(self, args):
        print('form created')
        self.form_el = jQuery(f"#{self.form_id}")[0]
        self.form_el.addEventListener('keypress', form_submit)

    def destroy(self):
        self.form.destroy()
        self.container_el.remove()

    def before_open(self, args):
        if not self.fullscreen:
            args.maxHeight = '80vh'

    def form_open(self, args):
        print('form open')
        # try:
        # if not self.data:
        #     print('no data')
        #     instance_data = {x: self.default_data[x] for x in self.default_data
        #                      if x in self.class_name._attributes or x in self.class_name._relationships}
        #     self.data = self.class_name(**instance_data)
        #     self.data = self.default_data
        print(self.data)
        for field in [x for x in self.form_fields if not x.is_dependent and x not in self.subforms]:
            # print(field.name)
            field.show()
            if field.name and getattr(self.data, field.name, None):
                field.value = self.data[field.name]
        for field in [x for x in self.form_fields if x.is_dependent]:
            # print(field.name, self.data)
            field.value = self.data
            field.show()
        for subform in self.subforms:
            subform.value = self.data
        for field in self.form_fields:
            if field.on_change is not None:
                # print('on_change', field.name)
                field.on_change({'name': field.name, 'value': field.value})
        self.container_el.style.visibility = 'visible'
        self.form.cssClass = 'e-fixed py-dialog'
        if self.form_tabs is not None:
            for i in range(len(self.form_tabs) - 1, -1, -1):
                self.tabs.select(i)
        # except Exception as e:
        #     print('exception', e)

        if self.validation is not None:
            self.validation['customPlacement'] = lambda input_el, error: \
                input_el.parentElement.parentElement.appendChild(error)
            self.validator = ej.inputs.FormValidator(f"#{self.form_id}", self.validation)
        print('form open end')

    def form_validate(self):
        print('Validation')
        return self.validator.validate() if self.validator is not None else True

    def form_save(self, args):
        print('SAVE', self.class_name, self.persist)
        # args.cancel = True
        if self.form_validate():
            add_new = False
            input_data = {field.name: field.value for field in self.form_fields
                          if field.save and not field.is_dependent}
            print('New Data: ', input_data, self.action)
            if self.action == 'edit' and hasattr(self.data, 'uid'):
                self.data.update(input_data)
            else:
                add_new = True
                self.data = self.class_name(**input_data)
            if self.persist:
                self.data.save()
                self.data = self.class_name.get(self.data.uid)
                # save subform rows
                for field in [x for x in self.form_fields if x.save and x.is_dependent]:
                    field.save_dependent(self.data)
                if self.subforms:
                    for subform in self.subforms:
                        subform.save_rows(self.data)
                for field in self.form_fields:
                    field.hide()
                    field.value = None
            self.form.hide()
            if self.update_source is not None:
                self.update_source(self.data, add_new)
                print('update_source', self.data)
        else:
            args.cancel = True
            print('Invalid Data')

    def form_cancel(self, args):
        print('CANCEL BASE')
        # args.cancel = True
        for field in self.form_fields:
            field.value = None
            field.hide()
        # self.form_fields = []
        self.form.hide()


# Basic class to build a subform grid on a form
class SubformBase:
    def __init__(self, name=None, fields=None, model=None, link_model=None, link_field=None, data=None, rows=None,
                 container_id=None, on_change=None, save=True, **kwargs):
        self.name = name
        self.model = model
        self.model_class = getattr(AppEnv.data_models, self.model) if self.model else None
        self.link_model = link_model
        self.link_field = link_field
        self.fields = fields
        self.container_id = container_id if container_id is not None else new_el_id()
        self.el_id = new_el_id()
        self.save = save
        self.html = f'<div id="{self.el_id}"></div>'
        self.visible = False
        self.on_change = on_change
        self.data = data if data is not None else []
        self.deleted = []

        grid_columns = [field.grid_column for field in self.fields]
        self.control = ej.grids.Grid({
            'toolbar': ['Add', 'Edit', 'Delete', 'Update', 'Cancel'],
            'editSettings': {
                'allowEditing': True,
                'allowAdding': True,
                'allowDeleting': True,
                'showConfirmDialog': True,
                'showDeleteConfirmDialog': True,
                'mode': 'Normal',
                'newRowPosition': 'Bottom'
            },
            'columns': grid_columns,
            'dataSource': [],
            'actionComplete': self.change,
            # 'cellSave': '',
            'gridLines': 'Default',
            'allowScrolling': True,
            'allowTextWrap': True,
            'textWrapSettings': {'wrapMode': 'Content'},
        })

    @property
    def value(self):
        value = []
        for row in self.control.dataSource:
            row_value = {}
            for field in self.fields:
                if field.save is True:
                    row_value[field.name] = row[f'{field.name}_serialized'] if hasattr(field, 'serialized') else row[
                        f'{field.name}_orm']
            value.append(row_value)
        return value

    @value.setter
    def value(self, value):
        if self.model is None:
            self.data = value
        else:
            self.grid_data = self.grid_class.get_grid_view(self.view_config,
                                                           search_queries=self.search_queries,
                                                           filters=self.filters,
                                                           include_rows=False)
            rows = self.model_class.search(**{self.link_field: value})
            self.data = []
            for obj in rows:
                subgrid_row = obj.to_grid()
                subgrid_row['obj'] = obj
                subgrid_row['state'] = ''
                self.data.append(subgrid_row)
        self.control.dataSource = self.data

    @property
    def rows(self):
        rows = [
            {field.name: row[f'{field.name}_orm'] if field.save is True else row[field.name] for field in self.fields}
            for row in self.control.dataSource]
        return rows

    @property
    def control(self):
        return self._control

    @control.setter
    def control(self, value):
        self._control = value

    def show(self):
        if not self.visible:
            anvil.js.window.document.getElementById(self.container_id).innerHTML = self.html
            if self._control is not None:
                self.control.appendTo(f"#{self.el_id}")
            self.visible = True

    def hide(self):
        if self.visible:
            anvil.js.window.document.getElementById(self.container_id).innerHTML = ''
            self.visible = False

    def change(self, args):
        if args.requestType not in ('save', 'delete'):
            return
        if self.model is not None:
            if args.requestType == 'delete':
                self.deleted.append(args.data['obj'])
            elif args.requestType == 'save':
                args.data['state'] = 'save'
        for field in self.fields:
            if field.save:
                args.data[f'{field.name}_orm'] = field.value
                if hasattr(field, 'serialized'):
                    args.data[f'{field.name}_serialized'] = field.serialized
        print('change', args.data)
        if self.on_change is not None:
            self.on_change({'name': self.name, 'value': self.value})

    def save_rows(self, link_obj=None):
        if self.model is not None:
            model_class = getattr(AppEnv.data_models, self.model, None)
            # model_attrs = model_class._attributes
            for obj in self.deleted:
                obj.delete()
            for row in self.control.dataSource:
                if row['state'] == 'save':
                    new_data = {field.name: row[f'{field.name}_orm'] for field in self.fields if field.save is True}
                    if 'obj' in row:
                        row['obj'].update(new_data)
                        row['obj'].save()
                    else:
                        new_data[self.link_field] = link_obj
                        model_class(**new_data).save()
