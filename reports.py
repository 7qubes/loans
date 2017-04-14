from openerp import api, models

class Loans_Register(models.AbstractModel):
    _name = 'sacco_loans.loans_register'
    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('sacco_loans.loans_register')
        docargs = {
            'doc_ids': self._ids,
            'doc_model': sacco.loan,
            'docs': self,
        }
        return report_obj.render('sacco_loans.loans_register', docargs)