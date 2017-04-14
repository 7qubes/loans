from openerp import models, fields, api
class loans_register_wizard(models.TransientModel):
	_name = 'loans_register_wizard'

	start_date = fields.Date()
	end_date = fields.Date()
	show = fields.Selection([('all','All'),('unposted','Unposted'),('posted','Posted'),('cleared','Cleared'),('defaulted',"Defaulted")], default = 'all')
	loan_product = fields.Many2one('sacco.loan.types')

	@api.multi
	def print_register(self):
		'''
		a document with filter satisfies a true && set operation for a combination of the and operations applied to its recordsets
		'''
		#date set
		if self.start_date:
			start_date_set = self.env['sacco.loan'].search([('application_date','>=',self.start_date)])
		else:
			start_date_set = self.env['sacco.loan'].search([])#this returns all records for the set operation if no filter is selected
		if self.end_date:
			end_date_set = self.env['sacco.loan'].search([('application_date','<=',self.end_date)])
		else:
			end_date_set = self.env['sacco.loan'].search([])#this returns all records for the set operation if no filter is selected

		#product set
		if self.loan_product:
			product_set = self.env['sacco.loan'].search([('loan_product_type','=',self.loan_product.id)])
		else:
			product_set = self.env['sacco.loan'].search([])

		#show set
		if self.show == 'cleared':
			show_set = self.env['sacco.loan'].search([('cleared','=',True)])
			#show_set = self.env['sacco.loan'].search([('loan_balance','<=',0)])
		elif self.show == 'unposted':
			show_set = self.env['sacco.loan'].search([('posted','=',False)])

		elif self.show == 'posted':
			show_set = self.env['sacco.loan'].search([('posted','=',True)])

		elif self.show == 'defaulted':
			show_set = self.env['sacco.loan'].search([('defaulted','=',True)])

		else:#show all
			show_set = self.env['sacco.loan'].search([])
			#show_set = self.env['sacco.loan'].search([('defaulted','=',True)])
		#set operation here
		register = start_date_set & end_date_set & show_set & product_set

		return self.env['report'].get_action(register,'sacco_loans.loans_register')



