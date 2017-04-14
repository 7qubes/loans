# -*- coding: utf-8 -*-

from openerp import models, fields, api,exceptions
from openerp.exceptions import ValidationError
import time
from datetime import datetime
from openerp.tools import amount_to_text_en
from openerp.tools.amount_to_text_en import amount_to_text


def calc_interest(amount,installments,interest,risk,repayment_method):
		#this function calculates and returns interest and principal and risk for all calculation methods

		principal = 0.0
		interest_calculated = 0.0
		schedule = []
		if repayment_method == 'straight':
			loan_balance = 0.0
			principal = round((amount/installments),2)#each month
			monthly_principal = [principal for x in range(1,installments + 1 )]#creates a list of straigt line principals
			loan_balance += principal#poor way of making it start from the actual loan balance. Find a better way later
			monthly_balances = []
			for item in monthly_principal:
				loan_balance -= principal
				monthly_balances.append(loan_balance)
			monthly_risk = [x*risk/1200 for x in monthly_balances]#get risk amount
			interest_calculated = round((principal*interest*0.01),2)
			monthly_interest = [interest_calculated for x in range(1,installments + 1 )]#creates a list of straigt line principals

			schedule = [monthly_principal,monthly_interest,monthly_risk]

		elif repayment_method == 'reducing':
			loan_balance = amount
			principal = round((amount/installments),2)#monthly installments
			monthly_principal = [principal for x in range(1,installments + 1 )]
			loan_balance += principal#poor way of making it start from the actual loan balance. Find a better way later
			monthly_balances = []
			for item in monthly_principal:
				loan_balance -= principal
				monthly_balances.append(loan_balance)
			monthly_interest = [round((x*interest/1200),2) for x in monthly_balances]
			monthly_risk = [round((x*risk/1200),2) for x in monthly_balances]#get risk amount
			schedule = [monthly_principal,monthly_interest,monthly_risk]
		elif repayment_method == 'amortized':
			loan_balance = amount
			monthly_principal = []
			monthly_interest = []
			monthly_risk = []
			monthly_rate = interest/1200
			monthly_repayment_amount = (monthly_rate/(1-(1+monthly_rate)**-installments))*amount
			for item in range(1,installments + 1):
				principal = monthly_repayment_amount - (loan_balance*interest/1200)

				monthly_principal.append(round(principal,2))
				monthly_interest.append(round((loan_balance*interest/1200),2))
				monthly_risk.append(round((loan_balance*risk/1200),2))
				loan_balance -= principal
			schedule = [monthly_principal,monthly_interest,monthly_risk]


		return schedule

def next_date(startdate_param):
		"""
		This next function calculates the next month with same date. If that date is larger than available dates for the
		following month, it gets the maximum date for that month:::>>>Author:dennokorir
		"""
		#we create a dictionary for months against their max days
		months_structure = {1:31,2:28,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}
		#start calculation
		start_date = datetime.strptime(str(startdate_param),'%Y-%m-%d').date()#start_date
		current_month = start_date.month
		current_year = start_date.year
		next_month = 0
		next_year = current_year
		if current_month == 12:
			next_month = 1
			next_year += 1
		else:
			next_month = current_month + 1

		#routine to ensure we do not exceed the number of days in the next month
		end_day = start_date
		current_day = start_date.day
		if current_day < months_structure[next_month]:
			end_day = start_date.replace(month = next_month, year = next_year)
		else:
			end_day = start_date.replace(day=months_structure[next_month],month=next_month, year = next_year)#months_structure[next_month] returns max days of next month
			#end_day = start_date.replace(month=next_month)
		return end_day

def month_ranges(startdate_param):
	'''
	This function will return the first and last days of the month in an array
	'''
	months_structure = {1:31,2:28,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}
	date_range = []
	start_date = datetime.strptime(str(startdate_param),'%Y-%m-%d').date()
	start_date = start_date.replace(day=1)
	current_month = start_date.month
	end_date = start_date.replace(day=months_structure[current_month])
	date_range = [start_date, end_date]
	return date_range

class loans(models.Model):
	_name = 'sacco.loan'

	name = fields.Char(string = 'Loan No.')
	application_date = fields.Date(default = fields.Date.today)
	loan_product_type = fields.Many2one('sacco.loan.types', string = "Loan Type" ,store = True)
	installments = fields.Integer()
	interest = fields.Float()
	interest_calculation_method = fields.Selection([('zero',"Zero Interest"),('flat',"Flat Rate"),('reducing',"Reducing Balance")])
	requested_amount = fields.Float()
	approved_amount = fields.Float(readonly = True, store = True)
	loan_balance = fields.Float(compute = 'get_loan_stats')
	loan_balance_due = fields.Float(compute = 'get_loan_stats')
	interest_due = fields.Float(compute = 'get_loan_stats')#shows balance according to schedule
	interest_balance = fields.Float(compute = 'get_loan_stats')#shows balance according to ledger
	insurance = fields.Float()
	status = fields.Selection([('draft',"Draft"),('appraisal',"Pending Appraisal"),('pending',"Pending Approval"),('approved',"Approved"),('rejected',"Rejected")], default = 'draft')
	issued_date = fields.Date()
	loan_disbursement_date = fields.Date()
	max_installments = fields.Integer()
	max_loan_amount = fields.Float()
	appraisal_status = fields.Selection([('interest',"Expression of Interest"),('desk',"Desk Appraisal")])
	repayment_start_date = fields.Date()
	member_no = fields.Many2one('sacco.member', store = 'True')
	member_name = fields.Char()
	staff_no = fields.Char()
	#no_of_guarantors = fields.Integer()
	guaranteed_amount = fields.Float(compute = 'sum_guarantors', readonly = True)#
	guaranteed_amount_percentage = fields.Float(compute = 'sum_guarantors', string = 'Percentage Guaranteed')#
	defaulted = fields.Boolean()
	batch_no = fields.Many2one('sacco.loan.batch.header' ,string = 'Loan Batch',domain = [('posted','=',False)],store = True)
	guarantor_id = fields.One2many('sacco.loan.guarantors','loan_no')#link to guarantor subpage
	guarantors = fields.Integer(compute = 'sum_guarantors',readonly = True)
	loan_security_id = fields.One2many('sacco.loan.securities','loan_no')#link to securities subpage
	loan_purpose = fields.Text()
	#salary details############################################################
	payrollno = fields.Char()
	basic_pay = fields.Float()#compute = 'get_payroll_stats'
	earnings = fields.Float()
	deductions = fields.Float()
	net_pay = fields.Float(compute = 'compute_payslip_stats')
	expected_repayment_deduction = fields.Float(compute = 'compute_payslip_stats')
	expected_net_pay = fields.Float(compute = 'compute_payslip_stats')
	###########################################################################
	idno = fields.Char()
	posted = fields.Boolean(default = False)
	topup_id = fields.One2many('sacco.loan.topups','loan_no') #reference to topups
	employer_code = fields.Many2one('sacco.employer')#'sacco.employer',compute = 'get_payroll_stats'
	schedule_ids = fields.One2many('sacco.loan.repayment.schedule','no')
	cleared = fields.Boolean()#compute = 'check_clearance'
	defaulted = fields.Boolean()#compute = 'check_defaulted'



	@api.one
	@api.depends('posted','schedule_ids')
	def get_loan_stats(self):
		if self.posted:
			ledger = self.env['sacco.member.ledger.entry'].search([('transaction_no','=',self.name)])
			if len(ledger)>0:
				loan_bal = 0.0
				loan_bal_due = 0.0
				interest_paid = 0.0
				interest_due = 0.0
				for line in ledger:
					if line.transaction_type == 'loan':
						loan_bal += line.amount
					elif line.transaction_type == 'interest':
						interest_paid += line.amount
					else:
						do_nothing = True#arbitrary
				self.loan_balance = loan_bal
				#we calculate interest due using current date and schedule ids
				if len(self.schedule_ids)>0:
					for item in self.schedule_ids:
						if datetime.strptime(item.period_paid,'%Y-%m-%d') <= datetime.now() and item.principal_paid == False:#schedule lines that have become due and principal amount have not been repaid by indiscretionary payments
							interest_due += item.interest
							loan_bal_due += item.principal
					self.interest_due = interest_due
					self.loan_balance_due = loan_bal_due
					if interest_paid > interest_due:
						self.interest_balance = 0.0
					else:
						self.interest_balance = interest_due - interest_paid


	@api.one
	@api.onchange('name')
	def get_sequence(self):
		setup = self.env['sacco.setup'].search([('id','=',1)])
		sequence = self.env['ir.sequence'].search([('id','=',setup.loan_application_nos.id)])
		self.name = sequence.next_by_id(sequence.id, context = None)


	@api.onchange('loan_product_type')
	def populate_loan_product_type(self):
		product = self.env['sacco.loan.types'].search([('id','=',self.loan_product_type.id)])

		self.interest = product.interest_rate
		self.installments = product.no_of_installments

		self.max_loan_amount = product.max_loan_amount

	@api.one
	@api.depends('basic_pay','earnings','deductions','expected_repayment_deduction')
	def compute_payslip_stats(self):
		if self.installments:
			self.expected_repayment_deduction = round((self.requested_amount/self.installments), 2)
		self.net_pay = self.basic_pay + self.earnings - self.deductions
		self.expected_net_pay = self.basic_pay + self.earnings - self.deductions - self.expected_repayment_deduction


	@api.onchange('member_no')
	def get_name(self):
		member = self.env['sacco.member'].search([('id','=',self.member_no.id)])
		setup = self.env['sacco.setup'].search([('id','=','1')])
		import datetime#temporary fix
		#check if member has spent enough time with sacco to request for a loan
		try:
			date_eligible = datetime.datetime.strptime(str(self.member_no.registration_date),'%Y-%m-%d').date() + datetime.timedelta(setup.member_grace_period*365/12)
		except:
			date_eligible = datetime.date.today() - datetime.timedelta(days = 1)#they will be eligible from yesterday if grace period not setup

		if date_eligible > datetime.date.today():
			return{
			'warning':{
			'title':"Member Loan Eligibility Grace Period",
			'message':"This member has not stayed in the sacco long enough to request for a Loan"
			}
			}

		#get member details
		self.member_name = member.name
		self.employer_code = member.employer_code
		self.payrollno = member.payrollno
		if member.current_loan >0.0:
			return{
								'warning':{
										'title':"Outstanding Loan",
										'message':"This member has an outstanding loan. This loan request if NOT EMERGENCY will not be fully processed",
								},
						}




	@api.one
	def generate_schedule(self):
		#delete first then generate schedule


		if self.issued_date:
			self.env['sacco.loan.repayment.schedule'].search([('no','=',self.id)]).unlink()
			repayment_schedule = self.env['sacco.loan.repayment.schedule']
			loan_product = self.env['sacco.loan.types'].search([('id','=',self.loan_product_type.id)])
			risk_setup = self.env['sacco.setup'].search([('id','=',1)])
			risk = risk_setup.risk_percentage
			loan_schedule = calc_interest(self.approved_amount,self.installments,self.interest,risk,loan_product.repayment_method)
			principal = loan_schedule[0]
			interest = loan_schedule[1]
			risk = loan_schedule[2]
			start_date = self.issued_date
			installment = 0
			balance = self.approved_amount
			for item in principal:

				installment += 1
				schedule_period_paid = next_date(start_date)
				start_date = next_date(start_date)#increment for next loop
				repayment_schedule.create({'no':self.id,'installment':installment,'period_paid':schedule_period_paid,'loan_balance':balance,'principal':item,'interest':interest[installment-1],'risk':risk[installment-1]})
				balance -= item
		else:
			raise exceptions.ValidationError("Issue date must have a value before generating schedule")


	@api.one
	@api.depends('guarantor_id')
	def sum_guarantors(self):
		self.guarantors = len(self.guarantor_id)
		amount_guaranteed = 0.0
		for item in self.guarantor_id:
			amount_guaranteed += item.amount_guaranteed
		self.guaranteed_amount = amount_guaranteed
		percentage_guaranteed = 0.0
		if self.guaranteed_amount > self.approved_amount:
			percentage_guaranteed = 100.0
		elif self.approved_amount == 0.0:
			percentage_guaranteed = 0.0
		else:
			percentage_guaranteed = self.guaranteed_amount/self.approved_amount*100
		self.guaranteed_amount_percentage = percentage_guaranteed


	'''
	@api.one
	@api.constrains('approved_amount','guaranteed_amount')
	def _check_guarantee(self):
		if self.approved_amount > self.guaranteed_amount:
			raise exceptions.ValidationError("Approved amount should not be greater than guaranteed amount")
		end = True

	'''
	@api.onchange('requested_amount','approved_amount')
	def check_amounts(self):
		start = True
		if self.approved_amount > self.requested_amount:
			self.approved_amount = 0.0
			return{'warning':{'title':"Approved Amount Error",'message':"Approved amount should not be greater than requested amount",},}


	@api.one
	@api.depends('posted')
	def check_clearance(self):
			if self.posted:
				if self.loan_balance<=0:
					self.cleared = True

	@api.one
	@api.depends('loan_balance_due')#,'cleared'
	def check_defaulted(self):
		if self.posted == True and self.loan_balance_due>0:# and not self.cleared
			self.defaulted = True
		else:
			self.defaulted = False
			'''
			schedule = self.env['sacco.loan.repayment.schedule'].search([('no','=',self.id),('period_paid','<',datetime.now().strftime("%Y/%m/%d")),('principal_paid','=',False)])
			if len(schedule)>0:
				self.defaulted = True
			else:
				self.defaulted = False
			'''
	@api.one
	def appraise_loan(self):
		setup = self.env['sacco.setup'].search([('id','=','1')])
		#check if member has spent enough time with sacco to request for a loan
		import datetime
		try:
			date_eligible = datetime.datetime.strptime(str(self.member_no.registration_date),'%Y-%m-%d').date() + datetime.timedelta(setup.member_grace_period*365/12)
		except:
			date_eligible = datetime.date.today() - datetime.timedelta(days = 1)#they will be eligible from yesterday if grace period not setup

		if date_eligible > datetime.date.today():
			raise ValidationError("Member has not spent the required time (%s months) to apply for a loan" %(setup.member_grace_period))

				#start computing to check for different appraisal limits
		approved_amount = [] #we'll store all maximum approved amounts depending on the different rules then pick the least as approved amount
		approved_amount.append(self.requested_amount)
		self.env['sacco.loan.appraisal.card'].search([('name','=',self.id)]).unlink()
		warnings = []
		#check shares
		share_multiplier_credit = 0.0
		share_multiplier_balance = 0.0
		if self.loan_product_type.appraise_deposits:
			share_multiplier_check = False
			share_multiplier_balance = self.member_no.current_deposits-self.member_no.current_loan
			if self.loan_product_type.share_multiplier > 0:
				share_multiplier_credit = (self.member_no.current_deposits-self.member_no.current_loan)*self.loan_product_type.share_multiplier
			else:
				if (self.member_no.current_deposits-self.member_no.current_loan) > 0:
					share_multiplier_credit = self.member_no.current_deposits-self.member_no.current_loan
				else:
					share_multiplier_credit = 0

			if share_multiplier_credit>=self.requested_amount:
				share_multiplier_check = True
			else:
				warnings.append({'name':'Share Multiplier Warning','description':'Current Shares do not meet share multiplier requirements'})

			#credit available from share multiplier
			approved_amount.append(max([share_multiplier_credit,0]))#share multiplier credit might result in a -ve. return 0 if so
		else:
			share_multiplier_check = True

		#check salary
		salary_rule_factor = 1
		if self.loan_product_type.appraise_salary:
			salary_rule_check = False
			salary_rule_factor = 0.0
			if self.basic_pay>0:
				salary_rule_factor = round((self.expected_net_pay/self.basic_pay),2)
				if (salary_rule_factor) > 0.33:#round((1/3),2))
					salary_rule_check = True

			else:
				warnings.append({'name':'1/3 Salary Rule Warning', 'description':'The requested amount repayment does not satisfy 1/3 salary rule requirements'})

			#credit available from salary rule
			'''
			We'll use this formula
			deduction = net_pay - (1/3*basic_pay)
			approved_amount = deduction * installments
			#this way, we can get the max allowable amount for their salary
			'''
			deduction = max([self.net_pay - (0.33*self.basic_pay),0])#the salary rule might result in a -ve. If so, approve 0
			approved_amount.append(deduction * self.installments)

		else:
			salary_rule_check = True



		#check guarantors
		if self.loan_product_type.appraise_guarantors:
			guarantors_check = False
			if self.guaranteed_amount >= self.requested_amount:
				guarantors_check = True
			else:
				warnings.append({'name':'Guarantor Warning','description':'This loan is not fully secured by the Guarantors'})

			#credit available from guarantors
			approved_amount.append(self.guaranteed_amount)
		else:
			guarantors_check = True

		self.approved_amount = min(approved_amount)#the minimum amount from the three rules

		if (share_multiplier_check and salary_rule_check and guarantors_check):
			self.status = 'pending'
		else:
			self.status = 'appraisal'

		appraisal = self.env['sacco.loan.appraisal.card'].create({'name':self.id,'share_multiplier':self.loan_product_type.share_multiplier,
			'share_multiplier_credit':share_multiplier_credit, 'share_multiplier_balance':share_multiplier_balance,'share_multiplier_check':share_multiplier_check,
			'salary_rule_check':salary_rule_check, 'salary_rule_factor':salary_rule_factor, 'guarantors_check':guarantors_check})

		for warning in warnings:
			self.env['sacco.loan.appraisal.warnings'].create({'header_id':appraisal.id,'name':warning['name'],'description':warning['description']})



	@api.multi
	def print_appraisal_report(self):
		loan_appraisal = self.env['sacco.loan.appraisal.card'].search([('name','=',self.id)])
		if len(loan_appraisal)>0:
			return self.env['report'].get_action(loan_appraisal, 'sacco_loans.loan_appraisal')

	@api.one
	def approve(self):
		self.status = 'approved'

	@api.one
	def reset_to_draft(self):
		self.status = 'draft'

class sacco_loan_appraisal(models.Model):
	_name = 'sacco.loan.appraisal.card'

	name = fields.Many2one('sacco.loan')
	share_multiplier = fields.Float()
	share_multiplier_credit = fields.Float()
	share_multiplier_balance = fields.Float()
	share_multiplier_check = fields.Boolean()
	salary_rule_check = fields.Boolean()
	salary_rule_factor = fields.Float()
	guarantors_check = fields.Boolean()
	warnings = fields.One2many('sacco.loan.appraisal.warnings','header_id', ondelete = 'cascade')

class sacco_loan_appraisal_warnings(models.Model):
	_name = 'sacco.loan.appraisal.warnings'

	header_id = fields.Many2one('sacco.loan.appraisal.card')
	name = fields.Char()
	description = fields.Char()

class loan_types(models.Model):

	_name = 'sacco.loan.types'

	code = fields.Char()

	name = fields.Char()
	source = fields.Selection([('fosa',"FOSA"),('bosa',"BOSA")])
	repayment_method = fields.Selection([('amortized',"Amortized"),('reducing',"Reducing Balance"),('straight',"Straight Line")])
	no_of_installments = fields.Integer()
	interest_rate = fields.Float()
	penalty_percentage = fields.Float()
	min_no_of_guarantors = fields.Integer()
	max_no_of_guarantors = fields.Integer()
	share_multiplier = fields.Float(default = 1.0)
	penalty_account = fields.Many2one('account.account')
	min_loan_amount = fields.Float()
	max_loan_amount = fields.Float()
	loan_account = fields.Many2one('account.account')
	loan_interest_account = fields.Many2one('account.account')
	receivable_interest_account = fields.Many2one('account.account')
	repayment_frequency = fields.Selection([('daily',"Daily"),('weekly',"Weekly"),('monthly',"Monthly"),('quarterly',"Quarterly"),('yearly',"Yearly")])
	insurance_percentage = fields.Float()
	write_off_account = fields.Many2one('account.account')
	appraise_deposits = fields.Boolean()
	appraise_salary = fields.Boolean()
	appraise_guarantors = fields.Boolean()
	appraise_collateral = fields.Boolean()
	appraise_self_guarantee = fields.Boolean()
	grace_period = fields.Integer()

class loan_guarantors(models.Model):
	_name = 'sacco.loan.guarantors'

	loan_no = fields.Many2one('sacco.loan')
	#member_no = fields.Char()
	name = fields.Many2one('sacco.member', store = 'True')
	loan_balance = fields.Float()
	shares = fields.Float()
	deposits = fields.Float()
	no_of_loans_guaranteed = fields.Integer()
	date = fields.Date(default = fields.Date.today)
	amount_guaranteed = fields.Float()
	percentage_guaranteed = fields.Float()
	id_no = fields.Char()
	member_guaranteed = fields.Char()

	total_guaranteed = fields.Float()

	@api.onchange('name')
	def get_guarantor_stats(self):
		self.shares = self.name.current_shares
		self.deposits = self.name.current_deposits

class sacco_securities(models.Model):
	_name = 'sacco.loan.securities'


	loan_no = fields.Many2one('sacco.loan')
	name = fields.Selection([('title','Title Deed'),('bank','Bank Guarantee'),('asset','Asset'),('other','Other')]
		,string = 'Type')
	description = fields.Char(string = 'Security Details')
	value = fields.Float()
	guarantee_value = fields.Float()
	remarks = fields.Text()

class loan_batch(models.Model):
	_name = 'sacco.loan.batch.header'

	name = fields.Char(string = 'Batch No')
	batch_type = fields.Selection([('loans',"Loans")])
	description = fields.Char()
	posted = fields.Boolean()
	total_loan_amount = fields.Float(compute = 'compute_no_of_loans')
	no_of_loans = fields.Integer(compute = 'compute_no_of_loans')
	mode_of_disbursement = fields.Selection([('cash',"Cash"),('cheque',"Cheque")])
	cheque_no = fields.Char()
	posting_date = fields.Date()
	status = fields.Selection([('open','Open'),('approved','Approved'),('rejected','Rejected')],default = 'open')
	loan_ids = fields.One2many('sacco.loan','batch_no') #link to loan batch lines-->List of loans under this batch
	test = fields.Char()
	paying_bank_account = fields.Many2one('res.bank',store = True)
	paying_bank = fields.Many2one('account.journal',domain = [('type','=','bank')],store = True)

	@api.one
	@api.onchange('name')
	def get_sequence(self):
		setup = self.env['sacco.setup'].search([('id','=',1)])
		sequence = self.env['ir.sequence'].search([('id','=',setup.loan_batch_nos.id)])
		self.name = sequence.next_by_id(sequence.id, context = None)

	@api.one
	def action_post(self):
		"""
		The journal is structured like a document. We'll make a single entry for the header and several
		entries for the lines
		We need to populate the following tables::account_move and account_move_line
		"""
		#test to see if all loans have schedules before starting to post
		for loan in self.loan_ids:
			if len(loan.schedule_ids)<=0:#test to see if schedule exists
				raise exceptions.ValidationError("Schedule must be generated for loan "+self.loan_ids.name+" before posting")
			if loan.status != 'approved':
				raise exceptions.ValidationError("Loan "+loan.name+" must be approved before posting this batch")
		if not self.posted:
			#date
			if self.posting_date:
				today = self.posting_date
			else:
				today = datetime.now().strftime("%Y/%m/%d")
			setup = self.env['sacco.setup'].search([('id','=',1)])
			#create journal header
			journal = self.env['account.journal'].search([('id','=',setup.loans_journal.id)]) #get journal id
			#period
			period = self.env['account.period'].search([('state','=','draft'),('date_start','<=',today),('date_stop','>=',today)])
			period_id = period.id

			journal_header = self.env['account.move']#reference to journal entry


			move = journal_header.create({'journal_id':journal.id,'period_id':period_id,'state':'draft','name':self.name,
				'date':today})

			move_id = move.id

			#create journal lines

			journal_lines = self.env['account.move.line']

			loans = self.env['sacco.loan'].search([('batch_no','=',self.id)])

			member_ledger = self.env['sacco.member.ledger.entry']
			#get last entry no
			ledgers = self.env['sacco.member.ledger.entry'].search([])
			entries = [ledger.entry_no for ledger in ledgers]
			try:
				entry_no = max(entries)
			except:
				entry_no = 0

			#get required accounts for the transaction

			#setup = self.env['sacco.setup'].search([('id','=',1)])
			loan_acc = setup.loans_account.id
			bank = self.env['account.journal'].search([('id','=',self.paying_bank.id)])
			bank_acc = bank.default_credit_account_id.id
			loan_interest_acc = setup.loan_interest_account.id
			loan_interest_receivable_acc = setup.loan_interest_receivable_account.id
			loan_processing_fee_acc = setup.loan_processing_fee_acc.id
			processing_rate = setup.loan_processing_fee

			for loan in loans:
				#this section allows for any charges applicable to your loan to be made
				processing_fee = 0.0
				processing_fee = (processing_rate*0.01)*loan.approved_amount
				amount_to_disburse = 0.0
				amount_to_disburse = loan.approved_amount - processing_fee
				#post loan journal
				journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':loan.name +'::'+loan.member_no.name, 'account_id':loan_acc,'move_id':move_id,'debit':loan['approved_amount']})#loan debtor loan['member_name']
				journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':loan.name +'::'+loan.member_no.name, 'account_id':bank_acc,'move_id':move_id,'credit':amount_to_disburse})#bank account  loan['member_name']
				journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':loan.name +'::'+loan.member_no.name +'::Processing Fees','account_id':loan_processing_fee_acc,'move_id':move_id,'credit':processing_fee})#processing fees  loan['name']
				loan['posted'] = True
				#post member ledger entry
				member = self.env['sacco.member'].search([('id','=',loan['member_no'].id)])
				member_name = member.name
				entry_no += 1
				member_ledger.create({'member_no':loan['member_no'].id,'member_name':member_name,'date':today,'transaction_no':loan['name'],'transaction_name':'Loan Application','amount':loan['approved_amount'],
				'transaction_type':'loan','entry_no':entry_no})#,'transaction_type':'loan'
			#self.no_of_loans = counter
			move.post()
			self.posted = True



	@api.one
	@api.depends('loan_ids')
	def compute_no_of_loans(self):
		self.no_of_loans = len(self.loan_ids)
		loan_amount = 0.0
		for loan in self.loan_ids:
			loan_amount += loan['approved_amount']
		self.total_loan_amount = loan_amount


	@api.one
	def action_approve(self):
		self.status = 'approved'

	@api.one
	def action_reject(self):
		self.status = 'rejected'

	@api.one
	def action_approvals(self):
		"""
		We will have code for approvals here. Approval functionality yet to be done
		"""

class sacco_setup(models.Model):
	_name = 'sacco.setup'

	loans_journal = fields.Many2one('account.journal',string = 'Loans Journal',store = True)
	interest_journal = fields.Many2one('account.journal',string = 'Interest Journal',store = True)
	checkoff_journal = fields.Many2one('account.journal',string = 'Checkoff Journal',store = True)
	loans_account = fields.Many2one('account.account', string = 'Loans Account',store = True)
	loan_interest_account = fields.Many2one('account.account',string = 'Loan Interest Account',store = True)
	loan_interest_receivable_account = fields.Many2one('account.account',string = 'Loan Interest Receivable Account',store = True)
	registration_fee = fields.Float()
	registration_fee_acc = fields.Many2one('account.account',string = 'Registration Fee A/C')
	loan_processing_fee = fields.Float(string = "Loan Processing Fee Percentage")
	loan_processing_fee_acc = fields.Many2one('account.account',string = 'Loan Processing Fee A/C')
	miscellaneous_journal = fields.Many2one('account.journal')
	deposits_account = fields.Many2one('account.account')
	shares_account = fields.Many2one('account.account')
	risk_percentage = fields.Float()
	risk_account = fields.Many2one('account.account')
	unallocated_funds = fields.Many2one('account.account', string = "Unallocated Funds A/C", help = "Unallocated funds resulting from the checkoff process when employer remits more than is required")
	#################Numbering##########################################
	member_nos = fields.Many2one('ir.sequence', store = True)
	member_application_nos = fields.Many2one('ir.sequence', store = True)
	member_closure_nos = fields.Many2one('ir.sequence', store = True)
	member_activation_nos = fields.Many2one('ir.sequence', store = True)
	loan_application_nos = fields.Many2one('ir.sequence', store = True)
	loan_batch_nos = fields.Many2one('ir.sequence', store = True)
	receipt_nos = fields.Many2one('ir.sequence', store = True)
	payment_nos = fields.Many2one('ir.sequence', store = True)
	share_transfer_nos = fields.Many2one('ir.sequence', store = True)
	deposit_capitalization_nos = fields.Many2one('ir.sequence')
	dividend_nos = fields.Many2one('ir.sequence')
	####################################################################
	#opening Balances Journals & Accounts
	opening_receivable_journal = fields.Many2one('account.journal')
	opening_payable_journal = fields.Many2one('account.journal')
	opening_balance_equity = fields.Many2one('account.account',string = 'Opening Bal Equity A/C')
	loan_grace_period = fields.Integer(string = "Loan Grace Period", help = "Time in days before loan repayment starts getting calculated")
	member_grace_period = fields.Integer(string = "Loan Eligibility Grace Period", help = "Time in months before member is eligible to apply for a loan")
	paybill = fields.Many2one('account.journal',domain = [('type','=','bank')])

class loans_topup(models.Model):
	_name = 'sacco.loan.topups'

	loan_no = fields.Many2one('sacco.loan')
	loan_top_up = fields.Char()
	member_no = fields.Char()
	loan_type = fields.Char()
	principle_topup = fields.Float()
	interest_topup = fields.Float()
	total_topup = fields.Float()
	monthly_repayment = fields.Float()
	outstanding_balance = fields.Float()
	interest_rate = fields.Float()
	commission = fields.Float()

class loan_advice(models.Model):
	_name = 'sacco.loan.advice'

	name = fields.Char()
	date = fields.Date(default = fields.Date.today)
	amount = fields.Float()
	last_advice_date = fields.Date()
	created = fields.Boolean(default = False)
	line_ids = fields.One2many('sacco.loan.advice.lines','doc_no')

	@api.one
	def action_generate_advice(self):
		self.env['sacco.loan.advice.lines'].search([('doc_no','=',self.id)]).unlink()
		loans = self.env['sacco.loan'].search([('posted','=',True)])
		advice = self.env['sacco.loan.advice.lines']
		for loan in loans:
			#get member
			member = self.env['sacco.member'].search([('id','=',loan.member_no.id)])
			member_name = member['name']
			#get employer
			employer = self.env['sacco.employer'].search([('id','=',member.employer_code.id)])
			employer_name = employer['description']
			#get product
			product = self.env['sacco.loan.types'].search([('id','=',loan.loan_product_type.id)])
			product_name = product['name']
			#do calculations
			principal = 0.0
			interest = 0.0
			total = 0.0
			principal = loan.loan_balance_due
			interest = loan.interest_balance
			total = principal + interest
			if (interest >0 ) or (principal > 0):
				advice.create({'doc_no':self.id,'member_no':loan.member_no.id,'employer_code':loan.employer_code,'loan_no':loan.name,
					'loan_product':loan.loan_product_type.id,'loan_amount':loan.approved_amount,'principal_repayment':principal,
					'interest_repayment':interest,'member_name':member_name,'employer_name':employer_name,'loan_product_description':product_name,'total':total})
		self.created = True

	@api.onchange('date')
	def get_month(self):
		today = datetime.now()
		month = today.month
		year = today.year
		months = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}
		self.name = months[month] + " " + str(year)

class loan_advice_lines(models.Model):
	_name = 'sacco.loan.advice.lines'

	doc_no = fields.Many2one('sacco.loan.advice')
	member_no = fields.Char()
	member_name = fields.Char()
	employer_code = fields.Char()
	employer_name = fields.Char()
	loan_no = fields.Char()
	loan_product = fields.Char()
	loan_product_description = fields.Char()
	loan_amount = fields.Float()
	principal_repayment = fields.Float()
	interest_repayment = fields.Float()
	total = fields.Float()

class monthly_interest(models.Model):
	_name = 'sacco.monthly.interest'

	name = fields.Char()
	date = fields.Date(default = fields.Date.today)
	amount = fields.Float(compute = 'compute_total_amount')

	created = fields.Boolean(default = False)
	posted = fields.Boolean(default = False)
	line_ids = fields.One2many('sacco.monthly.interest.lines','doc_no')

	@api.onchange('date')
	def get_month(self):
		today = datetime.now()
		month = today.month
		year = today.year
		months = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}
		self.name = months[month] + " " + str(year)

	@api.one
	def action_generate_interest(self):
		self.env['sacco.monthly.interest.lines'].search([('doc_no','=',self.id)]).unlink()
		loans = self.env['sacco.loan'].search([('status','=','approved')])
		interest_line = self.env['sacco.monthly.interest.lines']

		for loan in loans:
			#get member
			member = self.env['sacco.member'].search([('id','=',loan.member_no.id)])
			member_name = member['name']
			#get product
			product = self.env['sacco.loan.types'].search([('id','=',loan.loan_product_type.id)])
			product_name = product['name']
			if loan.loan_balance_due > 0.0:
				#do calculations
				principal = 0.0
				interest = 0.0
				total = 0.0
				principal = loan.loan_balance_due
				interest = loan.interest_balance
				total = principal + interest

				interest_line.create({'doc_no':self.id,'member_no':loan['member_no'].id,'member_name':member['name'],'loan_no':loan['name'],
					'loan_product':loan['loan_product_type'].id,'loan_product_description':product_name,'loan_amount':loan['approved_amount'],
					'monthly_principal':principal,'monthly_interest':interest})

	@api.one
	def action_post(self):

		if not self.posted:


			#get required accounts for the transaction
			setup = self.env['sacco.setup'].search([('id','=',1)])
			interest_journal = setup.interest_journal.id
			loan_interest_acc = setup.loan_interest_account.id
			loan_interest_receivable_acc = setup.loan_interest_receivable_account.id
			member_ledger = self.env['sacco.member.ledger.entry']

			#create journal header
			journal = setup['interest_journal'].id
			#self.env['account.journal'].search([('code','=','LOANS')]) #get journal id

			period = max(self.env['account.period'].search([('state','=','draft')]))
			period_id = period.id

			journal_header = self.env['account.move']#reference to journal entry
			#date
			if self.date:
				today = self.date
			else:
				today = datetime.now().strftime("%Y/%m/%d")
			move = journal_header.create({'journal_id':journal,'period_id':period_id,'state':'draft','name':self.name + ' interest',
				'date':today})

			move_id = move.id

			#create journal lines

			journal_lines = self.env['account.move.line']

			lines = self.env['sacco.monthly.interest.lines'].search([('doc_no','=',self.id)])

			for line in lines:
				#post interest journal
				journal_lines.create({'journal_id':journal,'period_id':period_id,'date':today,'name':'Interest Receivable::'+line['member_name'],'account_id':loan_interest_receivable_acc,'move_id':move_id,'debit':line['monthly_interest']})
				journal_lines.create({'journal_id':journal,'period_id':period_id,'date':today,'name':'Interest','account_id':loan_interest_acc,'move_id':move_id,'credit':line['monthly_interest']})
			move.post()
			self.posted = True

	@api.one
	@api.depends('line_ids')
	def compute_total_amount(self):
		total = 0.0
		for line in self.line_ids:
			total += line['monthly_interest']
		self.amount = total

class monthly_interest_lines(models.Model):
	_name = 'sacco.monthly.interest.lines'

	doc_no = fields.Many2one('sacco.monthly.interest')
	member_no = fields.Char()
	member_name = fields.Char()
	loan_no = fields.Char()
	loan_product = fields.Char()
	loan_product_description = fields.Char()
	loan_amount = fields.Float()
	monthly_principal = fields.Float()
	monthly_interest = fields.Float()

class checkoff_header(models.Model):
	_name = 'sacco.checkoff.header'

	no = fields.Char()
	date = fields.Date(default = fields.Date.today)
	amount = fields.Float(compute = 'calculate_checkoff_amount')
	posted = fields.Boolean()
	status = fields.Selection([('open',"Open"),('pending',"Pending Approval"),('approved',"")])
	line_ids = fields.One2many('sacco.checkoff.lines','no')#field to link header and lines

	@api.one
	def action_validate_checkoffs(self):
		lines = self.env['sacco.checkoff.lines'].search([('no','=',self.id)])
		for line in lines:
			member = self.env['sacco.member'].search([('payrollno','=',line['pfno'])])
			line.member_no = member.id
			line.member_name = member.name
	@api.one
	@api.depends('line_ids')
	def calculate_checkoff_amount(self):
		total = 0
		for line in self.line_ids:
			total += line['amount']
		self.amount = total

	@api.onchange('date')
	def get_month(self):
		today = datetime.now()
		month = today.month
		year = today.year
		months = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}
		self.no = months[month] + " " + str(year)

	@api.one
	def action_post(self):
		if not self.posted:
			#date
			if self.date:
				today = self.date
			else:
				today = datetime.now().strftime("%Y/%m/%d")
			setup = self.env['sacco.setup'].search([('id','=',1)])
			#create journal header
			journal = self.env['account.journal'].search([('id','=',setup.checkoff_journal.id)]) #get journal id
			#period
			period = self.env['account.period'].search([('state','=','draft'),('date_start','<=',today),('date_stop','>=',today)])
			period_id = period.id

			journal_header = self.env['account.move']#reference to journal entry


			move = journal_header.create({'journal_id':journal.id,'period_id':period_id,'state':'draft','name':self.no,
				'date':today})

			move_id = move.id

			#create journal lines

			journal_lines = self.env['account.move.line']

			checkoff = self.env['sacco.checkoff.lines'].search([('no','=',self.id)])
			#get required accounts for the transaction
			setup = self.env['sacco.setup'].search([('id','=',1)])
			loan_acc = setup.loans_account.id
			bank = self.env['account.journal'].search([('id','=',setup.checkoff_journal.id)])
			bank_acc = bank.default_debit_account_id.id
			loan_interest_acc = setup.loan_interest_account.id
			loan_interest_receivable_acc = setup.loan_interest_receivable_account.id
			unallocated_acc = setup.unallocated_funds.id
			member_ledger = self.env['sacco.member.ledger.entry']

			#get last member ledger entry no.
			ledgers = self.env['sacco.member.ledger.entry'].search([])
			entries = [ledger.entry_no for ledger in ledgers]
			try:
				entry_no = max(entries)
			except:
				entry_no = 0
			"""
			We're going to recover outstanding amounts loan by loan. We first get the member then recover all amounts starting from the interest then
			principal amount in that order.
			"""
			for line in self.line_ids:
				member = self.env['sacco.member'].search([('member_account_status','=','active'),('id','=',line.member_no)])
				if len(member)>0:
					#search for member loans
					#raise ValidationError('Found Member')
					loans = self.env['sacco.loan'].search([('member_no','=',member.id)])
					if len(loans)>0:
						#raise ValidationError('Found Loans')
						#init running balance
						runningBal = line.amount
                        unallocated = 0.0
                        for loan in loans:
							#init parameters
							interest = 0.0
							principal = 0.0
							total = 0.0

							#start recovering loan by loan. start with interest then principal
							expected_interest = 0.0
							expected_interest = loan.interest_balance#(loan.approved_amount*loan.interest*0.01)/loan.installments
							if expected_interest<runningBal:
								interest = expected_interest
								runningBal-=expected_interest

							else:
								interest = runningBal
								runningBal = 0.0

							#start recovering principal amounts
							expected_principal = 0.0
							expected_principal = loan.loan_balance_due
							if expected_principal<runningBal:
								principal = expected_principal
								runningBal-=expected_principal
							else:
								principal = runningBal
								runningBal = 0.0

							#push remaining balance to unallocated
							#unallocated = runningBal

							if principal > 0.0:
								entry_no += 1
								journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':'Principal Repayment::'+ line['member_name'],'account_id':bank_acc,'move_id':move_id,'debit':principal})#
								journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':'Principal Repayment::'+ line['member_name'],'account_id':loan_acc,'move_id':move_id,'credit':principal})
								member_ledger.create({'member_no':loan['member_no'].id,'member_name':line['member_name'],'date':today,'transaction_no':loan['name'],'transaction_name':'Loan Repayment','amount':-(principal),'transaction_type':'loan','entry_no':entry_no})#post member ledger

							if interest > 0.0:
								entry_no += 1
								journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':'Interest Payment::'+ line['member_name'],'account_id':bank_acc,'move_id':move_id,'debit':abs(interest)})
								journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':'Interest Payment::'+ line['member_name'],'account_id':loan_interest_receivable_acc,'move_id':move_id,'credit':abs(interest)})
								member_ledger.create({'member_no':loan['member_no'].id,'member_name':line['member_name'],'date':today,'transaction_no':loan['name'],'transaction_name':'Interest Payment','amount':interest,'transaction_type':'interest','entry_no':entry_no})#post member ledger

						#push remaining balance to unallocated
                        unallocated = runningBal
                        if unallocated > 0.0:
							entry_no += 1
							journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':'Unallocated Funds::'+ line['member_name'],'account_id':bank_acc,'move_id':move_id,'debit':abs(unallocated)})
							journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':'Unallocated Funds::'+ line['member_name'],'account_id':unallocated_acc,'move_id':move_id,'credit':abs(unallocated)})
							member_ledger.create({'member_no':loan['member_no'].id,'member_name':line['member_name'],'date':today,'transaction_no':loan['name'],'transaction_name':'Unallocated Funds','amount':unallocated,'transaction_type':'unallocated','entry_no':entry_no})#post member ledger
			move.post()
			self.posted = True

class checkoff_lines(models.Model):
	_name = 'sacco.checkoff.lines'

	no = fields.Many2one('sacco.checkoff.header')#field to link header and lines
	pfno = fields.Char()
	member_no = fields.Char()
	member_name =fields.Char()
	amount = fields.Float()

class dividend_header(models.Model):
	_name = 'sacco.dividend.header'

	name = fields.Char()
	start_date = fields.Date()
	end_date = fields.Date()
	dividend_type = fields.Selection([('flat',"Flat Rate"),('prorated',"Prorated")], default = 'flat', required = True)
	dividend_rate = fields.Float()
	amount = fields.Float(compute = 'compute_totals', string = "Total Dividend Amount")
	state = fields.Selection([('draft',"Draft"),('confirmed',"Confirmed")], default = 'draft')
	line_ids = fields.One2many('sacco.dividend.lines','header_id')

	@api.one
	@api.onchange('name')
	def get_sequence(self):
		setup = self.env['sacco.setup'].search([('id','=',1)])
		sequence = self.env['ir.sequence'].search([('id','=',setup.dividend_nos.id)])
		self.name = sequence.next_by_id(sequence.id, context = None)

	@api.one
	def compute_dividends(self):
		self.line_ids.unlink()
		#flat rate
		if self.dividend_type == 'flat':
			members = self.env['sacco.member'].search([])
			for member in members:
				amount = 0.0
				dividend_amount = 0.0
				deposit_ledger = self.env['sacco.member.ledger.entry'].search([('member_no.id','=',member.id),('date','>=',datetime.strptime(self.start_date, '%Y-%m-%d')),('date','<=',datetime.strptime(self.end_date,'%Y-%m-%d'))])
				amount = sum(ledger.amount for ledger in deposit_ledger)
				dividend_amount = self.dividend_rate * 0.01 * amount
				self.env['sacco.dividend.lines'].create({'header_id':self.id,'member_no':member.no,'member_name':member.id,'qualifying_shares':amount,'gross_dividends':dividend_amount,'dividend_payable':dividend_amount})
		elif self.dividend_type == 'prorated':
			members = self.env['sacco.member'].search([])
			for member in members:
				amount = 0.0
				gross = 0.0
				dividend_amount = 0.0
				start = self.start_date#datetime.strptime(self.start_date, '%Y-%m-%d')
				while datetime.strptime(str(start), '%Y-%m-%d') < datetime.strptime(self.end_date, '%Y-%m-%d'):
					dates = month_ranges(start)
					deposit_ledger = self.env['sacco.member.ledger.entry'].search([('member_no.id','=',member.id),('date','>=',datetime.strptime(str(dates[0]), '%Y-%m-%d')),('date','<=',datetime.strptime(str(dates[1]), '%Y-%m-%d'))])
					amount = sum(ledger.amount for ledger in deposit_ledger)
					dividend_amount += self.dividend_rate * 0.01 * amount * (self.dividend_rate/12)
					gross += amount
					start = next_date(start)
				self.env['sacco.dividend.lines'].create({'header_id':self.id, 'member_no':member.no, 'member_name':member.id, 'qualifying_shares':gross,'gross_dividends':dividend_amount,'dividend_amount':dividend_amount,'dividend_payable':dividend_amount})


	@api.one
	def confirm(self):
		self.state = 'confirmed'

	@api.one
	def reset_to_draft(self):
		self.state = 'draft'

	@api.one
	def action_post(self):
		pass

	@api.one
	@api.depends('line_ids')
	def compute_totals(self):
		self.amount = sum(line.dividend_payable for line in self.line_ids)

class dividend_lines(models.Model):
	_name = 'sacco.dividend.lines'

	header_id = fields.Many2one('sacco.dividend.header')
	member_no = fields.Char()
	member_name = fields.Many2one('sacco.member')
	qualifying_shares = fields.Float()
	dividends = fields.Float()
	gross_dividends = fields.Float()
	withholding_tax = fields.Float()
	dividend_payable = fields.Float()

class repayment_schedule(models.Model):
	_name = 'sacco.loan.repayment.schedule'

	no = fields.Many2one('sacco.loan')
	installment = fields.Integer()
	period_paid = fields.Char()
	loan_balance = fields.Float()
	principal = fields.Float()
	interest = fields.Float()
	risk = fields.Float()
	total = fields.Float(compute = 'sum_total')
	principal_paid = fields.Boolean(compute = 'check')
	interest_paid = fields.Boolean(compute = 'check')

	@api.one
	@api.depends('no','period_paid')
	def check(self):
		#import math
		"""
		This routine will go making checkmarks on all repayment entries depending on the balance remaining
		"""
		loan = self.env['sacco.loan'].search([('id','=',self.no.id)])

		loan_no = loan.name
		ledgers = self.env['sacco.member.ledger.entry'].search([('transaction_no','=',loan_no)])#,('date','<=',self.period_paid)
		if len(ledgers)>0:#This is to avoid false checking if no loan has been posted.
			lines = self.env['sacco.loan.repayment.schedule'].search([('no','=',self.no.id),('period_paid','<=',self.period_paid)])
			#loan repayment
			loan_balance = 0.0
			for ledger in ledgers:

				if ledger.transaction_type == 'loan':
					loan_balance += ledger.amount
			principal_repayment = 0.0
			for line in lines:
				principal_repayment += line.principal
			expected_balance = loan.approved_amount - principal_repayment
			if loan_balance <= expected_balance:
				self.principal_paid = True
				self.interest_paid = True

	@api.one
	@api.depends('principal','interest','risk')
	def sum_total(self):
		if self.id:
			self.total = self.principal + self.interest# + self.risk

class receipt_header(models.Model):
	_name = 'sacco.receipt.header'

	name = fields.Char()
	date = fields.Date(default=fields.date.today())
	bank_code = fields.Many2one('account.journal',domain = [('type','=','bank')])
	bank_name = fields.Char()
	amount_received = fields.Float(compute = 'compute_total')#
	received_from = fields.Char()
	cashier = fields.Many2one('res.users', default=lambda self: self.env.user, readonly = True)
	posted = fields.Boolean()
	amount_words = fields.Char(compute = 'compute_total')
	line_ids = fields.One2many('sacco.receipt.line','no')
	licenses = fields.Selection([('vehicle',"Vehicle $ Transport"),('concert',"Concert, Exhibitions"),('cafe',"Restaurants, Cafe, Coffeshop"),
								('office',"Office Building & Factories"),('dance',"Dance"),('tv',"TV Broadcasts"),
								('shop',"Shops(Including Charity Shops)"),('college',"iniversity & Colleges"),('roadshow',"RoadShows"),
								('hair',"Hair Dressers(Beauty Shops)"),('ringtone',"Rindtone & Rindback"),
								('club',"Amatuer & Clubs"),('radio',"Radio, Outside Broadcasts"),
								('cinemas',"Cinemas & Theatres"),('rave',"Rave & Dance Parties")])


	@api.one
	@api.onchange('name')
	def get_sequence(self):
		setup = self.env['sacco.setup'].search([('id','=',1)])
		sequence = self.env['ir.sequence'].search([('id','=',setup.receipt_nos.id)])
		self.name = sequence.next_by_id(sequence.id, context = None)

	@api.one
	@api.onchange('bank_code')
	def get_bank(self):
		#get bank name
		bank = self.env['account.journal'].search([('id','=',self.bank_code.id)])
		self.bank_name = bank.name

	@api.one
	def action_post(self):
		if not self.posted:
			#date
			if self.date:
				today = self.date
			else:
				today = datetime.now().strftime("%m/%d/%Y")
			setup = self.env['sacco.setup'].search([('id','=',1)])
			#create journal header
			journal = self.env['account.journal'].search([('id','=',setup.miscellaneous_journal.id)]) #get journal id
			#period
			period = self.env['account.period'].search([('state','=','draft'),('date_start','<=',today),('date_stop','>=',today)])
			period_id = period.id

			journal_header = self.env['account.move']#reference to journal entry


			move = journal_header.create({'journal_id':journal.id,'period_id':period_id,'state':'draft','name':self.name,
				'date':today})

			move_id = move.id

			#create journal lines

			journal_lines = self.env['account.move.line']

			#get required accounts for the transaction
			#debit account
			bank = self.env['account.journal'].search([('id','=',self.bank_code.id)])
			bank_acc = bank.default_debit_account_id.id



			member_ledger = self.env['sacco.member.ledger.entry']

			ledgers = self.env['sacco.member.ledger.entry'].search([])
			entries = [ledger.entry_no for ledger in ledgers]
			try:
				entry_no = max(entries)
			except:
				entry_no = 0
			#post journal

			for line in self.line_ids:
				#credit account
				credit_acc = 0
				entry_type = ''
				transaction_name = ''
				create_ledger = False
				factor = 1 #we'll use this to choose whether the entry made on the member ledger is positive or negative
				if line.transaction_type == 'registration':
					#registration fee account
					create_ledger = False
					credit_acc = setup.registration_fee_acc.id
					transaction_no = self.name
					transaction_name = 'Member Registration'
				elif line.transaction_type == 'deposits':
					#liability account
					credit_acc = setup.deposits_account.id
					entry_type = 'deposits'
					transaction_name = 'Member Deposits'
					create_ledger = True
					transaction_no = self.name
				elif line.transaction_type == 'unallocated':
					#liability account
					credit_acc = setup.unallocated_funds.id
					entry_type = 'unallocated'
					transaction_name = 'Online Receipts'
					create_ledger = True
					transaction_no = self.name
				elif line.transaction_type == 'shares':
					#shares account
					credit_acc = setup.shares_account.id
					entry_type = 'shares'
					transaction_name = 'Member Shares'
					create_ledger = True
					transaction_no = self.name
				elif line.transaction_type == 'repayment':
					#debtor account
					loan = self.env['sacco.loan'].search([('id','=',line.loan_no.id)])
					credit_acc = setup.loans_account.id
					entry_type = 'loan'
					transaction_name = 'Loan Repayment'
					create_ledger = True
					transaction_no = loan.name
					factor = -1
				else:
					credit_acc = 0


				#quick bad solution
				if line.transaction_type != 'repayment':
					journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':credit_acc,'move_id':move_id,'credit':line.amount})
					journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':bank_acc,'move_id':move_id,'debit':abs(line.amount)})
					#post member ledger entry
					if create_ledger:
						entry_no += 1
						member = self.env['sacco.member'].search([('id','=',line['member_no'].id)])
						member_name = member.name
						member_ledger.create({'member_no':line.member_no.id,'member_name':member_name,'date':today,'transaction_no':transaction_no,'transaction_name':transaction_name + '::' + self.name,'amount':factor*line.amount,'transaction_type':entry_type,'entry_no':entry_no})

				else:
					#recover interest then principal
					member = self.env['sacco.member'].search([('id','=',line['member_no'].id)])
					member_name = member.name
					runBal = line.amount
					interest = 0.0
					principal = 0.0
					#unallocated = 0.0
					loan = self.env['sacco.loan'].search([('id','=',line.loan_no.id)])
					#recover interest
					if runBal >loan.interest_balance:
						interest = loan.interest_balance
						runBal -= interest
					else:
						interest = runBal
						runBal = 0
					#recover principal
					if runBal > 0:
						principal = runBal

					#else:
					#	principal = 'runBal'
					#	runBal = 0
					#record unallocated
					#if runBal > 0:
					#	unallocated = runBal

					if interest > 0:
						entry_no += 1
						journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':setup.loan_interest_account.id,'move_id':move_id,'credit':abs(interest)})
						journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':bank_acc,'move_id':move_id,'debit':abs(interest)})
						member_ledger.create({'member_no':line.member_no.id,'member_name':member_name,'date':today,'transaction_no':transaction_no,'transaction_name':transaction_name + '::' + self.name,'amount':interest,'transaction_type':'interest','entry_no':entry_no})

					if principal > 0:
						entry_no += 1
						journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':credit_acc,'move_id':move_id,'credit':abs(principal)})
						journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':bank_acc,'move_id':move_id,'debit':abs(principal)})
						member_ledger.create({'member_no':line.member_no.id,'member_name':member_name,'date':today,'transaction_no':transaction_no,'transaction_name':transaction_name + '::' + self.name,'amount':factor*principal,'transaction_type':entry_type,'entry_no':entry_no})
					'''
					if unallocated > 0:
						entry_no += 1
						journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':setup.unallocated_funds.id,'move_id':move_id,'credit':abs(unallocated)})
						journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':bank_acc,'move_id':move_id,'debit':abs(unallocated)})
						member_ledger.create({'member_no':line.member_no.id,'member_name':member_name,'date':today,'transaction_no':transaction_no,'transaction_name':transaction_name + '::' + self.name,'amount':factor*principal,'transaction_type':'unallocated'})
					'''
			move.post()
			self.posted = True


	@api.one
	@api.depends('line_ids')
	def compute_total(self):
		amount = 0
		for line in self.line_ids:
			amount += line.amount
		self.amount_received = amount
		self.amount_words = amount_to_text_en.amount_to_text(float(amount), "Shilling")

class receipt_line(models.Model):
	_name = 'sacco.receipt.line'

	no = fields.Many2one('sacco.receipt.header')
	transaction_type = fields.Selection([('registration',"Registration Fee"),('deposits',"Share Contribution"),('shares',"Shares Capital"),('repayment',"Loan Repayment"),('unallocated',"Unallocated Funds")])
	member_no = fields.Many2one('sacco.member')
	loan_no = fields.Many2one('sacco.loan', domain = [('posted','=',True)])
	description = fields.Char()
	amount = fields.Float()

class payment_header(models.Model):
	_name = 'sacco.payment.header'

	name = fields.Char()
	date = fields.Date(default=fields.date.today())
	bank_code = fields.Many2one('account.journal',domain = [('type','=','bank')])
	bank_name = fields.Char()
	amount = fields.Float(compute = 'compute_total')#compute = 'compute_total'
	amount_words = fields.Char(compute = 'compute_total')
	payment_to = fields.Char()
	on_behalf_of = fields.Char()
	payment_narration = fields.Text()
	cashier = fields.Many2one('res.users', default=lambda self: self.env.user, readonly = True)
	pay_mode = fields.Selection([('cash',"Cash"),('cheque',"Cheque")])
	cheque_no = fields.Char()
	status = fields.Selection([('open',"Open"),('pending',"Pending Approval"),('approved',"Approved"),('rejected',"Rejected")], default = 'open')
	posted = fields.Boolean()


	line_ids = fields.One2many('sacco.payment.line','no')

	@api.one
	def action_post(self):
		if not self.posted:
			if self.date:
				today = self.date
			else:
				today = datetime.now().strftime("%m/%d/%Y")
			setup = self.env['sacco.setup'].search([('id','=',1)])
			member_ledger = self.env['sacco.member.ledger.entry']

			ledgers = self.env['sacco.member.ledger.entry'].search([])
			entries = [ledger.entry_no for ledger in ledgers]
			try:
				entry_no = max(entries)
			except:
				entry_no = 0

			#initialize journals
			#create journal header
			journal = self.env['account.journal'].search([('id','=',setup.miscellaneous_journal.id)]) #get journal id
			#period
			period = self.env['account.period'].search([('state','=','draft'),('date_start','<=',today),('date_stop','>=',today)])
			period_id = period.id

			journal_header = self.env['account.move']#reference to journal entry


			move = journal_header.create({'journal_id':journal.id,'period_id':period_id,'state':'draft','name':self.name,
				'date':today})

			move_id = move.id

			#create journal lines

			journal_lines = self.env['account.move.line']

			#credit account
			bank = self.env['account.journal'].search([('id','=',self.bank_code.id)])
			bank_acc = bank.default_debit_account_id.id

			#debit account
			debit_acc = 0
			for line in self.line_ids:

				if line.transaction_type == 'withdrawal':
					debit_acc = setup.deposits_account.id

				elif line.transaction_type == 'dividend':
					pass #find out accounting for dividends

				#check if balance is enough
				member = self.env['sacco.member'].search([('id','=',line['member_no'].id)])
				if member.current_deposits < line.amount:
					raise ValidationError('Amount requested exceeds current deposits.')

				#start posting entries
				journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + self.name,'account_id':debit_acc,'move_id':move_id,'debit':self.amount})
				journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + self.name,'account_id':bank_acc,'move_id':move_id,'credit':self.amount})

				#post member ledger
				entry_no += 1
				member_name = member.name
				member_ledger.create({'entry_no':entry_no,'member_no':line.member_no.id,'member_name':member_name,'date':today,'transaction_no':self.name,'transaction_name':line.transaction_type + '::' + self.name,'amount':line.amount,'transaction_type':line.transaction_type})
			move.post()
			self.posted = True

		else:
			raise ValidationError("This payment has already been posted!")


	@api.one
	@api.onchange('name')
	def get_sequence(self):
		setup = self.env['sacco.setup'].search([('id','=',1)])
		sequence = self.env['ir.sequence'].search([('id','=',setup.payment_nos.id)])
		self.name = sequence.next_by_id(sequence.id, context = None)

	@api.one
	@api.onchange('bank_code')
	def get_bank(self):
		#get bank name
		bank = self.env['account.journal'].search([('id','=',self.bank_code.id)])
		self.bank_name = bank.name

	@api.one
	@api.depends('line_ids')
	def compute_total(self):
		self.amount = sum(line.amount for line in self.line_ids)
		self.amount_words = amount_to_text_en.amount_to_text(float(self.amount), "Shilling")

class payment_line(models.Model):
	_name = 'sacco.payment.line'

	no = fields.Many2one('sacco.payment.header')
	transaction_type = fields.Selection([('withdrawal',"Deposit Withdrawal"),('dividend',"Dividend")])
	member_no = fields.Many2one('sacco.member')
	description = fields.Char()
	amount = fields.Float()

class deposit_capitalization(models.Model):
	_name = 'sacco.deposit.capitalization'

	name = fields.Char()
	date = fields.Date(default=fields.date.today())
	description = fields.Char()
	member_name = fields.Many2one('sacco.member')
	deposits_balance = fields.Float()
	amount = fields.Float()
	status = fields.Selection([('open',"Open"),('pending',"Pending Approval"),('approved',"Approved")], default = 'open')
	posted = fields.Boolean()
	comment = fields.Text()

	@api.one
	@api.onchange('name')
	def get_sequence(self):
		setup = self.env['sacco.setup'].search([('id','=',1)])
		sequence = self.env['ir.sequence'].search([('id','=',setup.deposit_capitalization_nos.id)])
		self.name = sequence.next_by_id(sequence.id, context = None)

	@api.onchange('member_name')
	def get_deposits(self):
		self.deposits_balance = self.member_name.current_deposits

	@api.one
	def action_post(self):
		member = self.env['sacco.member'].search([('id','=',self.member_name.id)])
		if member.current_deposits < self.amount:
			raise ValidationError("Amount being transferred exceeds current member's deposits")
		if self.date:
			today = self.date
		else:
			today = datetime.now().strftime("%m/%d/%Y")

		ledgers = self.env['sacco.member.ledger.entry'].search([])
		entries = [ledger.entry_no for ledger in ledgers]
		try:
			entry_no = max(entries)
		except:
			entry_no = 0
		entry_no+=1
		member_ledger = self.env['sacco.member.ledger.entry']
		member_ledger.create({'entry_no':entry_no,'member_no':self.member_name.id,'member_name':member.name,'date':today,'transaction_no':self.no,'transaction_name':'Deposit Capitalization::'+self.description,'amount':-(self.amount),'transaction_type':'deposits'})
		entry_no +=1
		member_ledger.create({'entry_no':entry_no,'member_no':self.member_name.id,'member_name':member.name,'date':today,'transaction_no':self.no,'transaction_name':'Deposit Capitalization::'+self.description,'amount':self.amount,'transaction_type':'shares'})

		self.posted = True

class sacco_opening_balances(models.Model):
	_name = 'sacco.opening.balances'

	no = fields.Char()
	description = fields.Char()
	transaction_type = fields.Selection([('deposits',"Member Deposits"),('shares',"Shares Contribution"),('loan',"Loan")], default = 'deposits')
	date = fields.Date()
	line_ids = fields.One2many('sacco.opening.balances.lines','doc_no')
	validated = fields.Boolean()
	state = fields.Selection([('draft',"Draft"),('ready',"Ready")],default = 'draft')

	@api.one
	def validate(self):
		if not self.validated:
			#this function will check if all entries are correct and all setups required have been done.
			#this is meant to reduce errors during posting of opening entries

			#1.Check Setups
			setup = self.env['sacco.setup'].search([('id','=',1)])
			if not setup.opening_receivable_journal.id:
				raise ValidationError('Setup Error \n Opening Receivable Journal must have a value in Sacco Setup under Quickstart Options')
			if not setup.opening_payable_journal.id:
				raise ValidationError('Setup Error \n Opening Payable Journal must have a value in Sacco Setup under Quickstart Options')

			if not setup.opening_balance_equity.id:
				raise ValidationError('Setup Error \n Opening Balance Equity account must have a value in Sacco Setup under Quickstart Options')
			if not setup.deposits_account.id:
				raise ValidationError('Setup Error \n Deposits Account must have a value in Sacco Setup under Quickstart Options')

			#2.Check Entries
			if self.transaction_type in['deposits','shares']:
				for line in self.line_ids:
					member = self.env['sacco.member'].search([('no','=',line.member_no)])
					if len(member)>0:
						line.member_id = member.id
						line.member_name = member.name

					else:
						raise ValidationError('Member with Member No. '+ line.member_no + ' does not exist in the member table')
			elif self.transaction_type == 'loan':
				for line in self.line_ids:
					member = self.env['sacco.member'].search([('no','=',line.member_no)])
					if len(member)>0:
						line.member_id = member.id
						line.member_name = member.name

					else:
						raise ValidationError('Member with Member No. '+ line.member_no + ' does not exist in the member table')

					if not line.transaction_no:
						raise ValidationError('Ensure all lines have a value for Transaction No.')

					transaction_name = 'Loan Application'

					if line.loan_product_code:
						product = self.env['sacco.loan.types'].search([('code','=',line.loan_product_code)])
						if len(product)>0:
							line.loan_product_id = product.id
						else:
							raise ValidationError('Loan product with Code %s does not exist in the Loan Products table' %(line.loan_product_code))
					else:
						raise ValidationError('Loan Product Code must have a value for transaction type [Loans]')

			self.validated = True
			self.state = 'ready'


	@api.one
	def action_post_opening_entries(self):
		if self.validated:
			#create journal & post
			#date
			if self.date:
				today = self.date
			else:
				today = datetime.now().strftime("%m/%d/%Y")
			setup = self.env['sacco.setup'].search([('id','=',1)])
			#create journal header
			journal = self.env['account.journal'].search([('id','=',setup.opening_receivable_journal.id)]) #get journal id
			#period
			period = self.env['account.period'].search([('state','=','draft'),('date_start','<=',today),('date_stop','>=',today)])

			period_id = period.id

			journal_header = self.env['account.move']#reference to journal entry


			move = journal_header.create({'journal_id':journal.id,'period_id':period_id,'state':'draft','name':self.no,
				'date':today})

			move_id = move.id

			for line in self.line_ids:
				if self.transaction_type == 'deposits':


					#create journal lines

					journal_lines = self.env['account.move.line']


					#debit account
					equity_acc = setup.opening_balance_equity.id
					#credit account
					deposit_acc = setup.deposits_account.id

					journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.description,'account_id':equity_acc,'move_id':move_id,'debit':line.amount})
					journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.description,'account_id':deposit_acc,'move_id':move_id,'credit':line.amount})
					#post member ledger
					member = self.env['sacco.member'].search([('id','=',line.member_id)])
					member_name = member.name
					member_ledger = self.env['sacco.member.ledger.entry']
					member_ledger.create({'member_no':line.member_id,'member_name':line.member_name,'date':today,'transaction_no':self.no,'transaction_name':self.description,'amount':line.amount,'transaction_type':'deposits'})



				elif self.transaction_type == 'shares':
					#create journal & post
					journal_lines = self.env['account.move.line']


					#debit account
					equity_acc = setup.opening_balance_equity.id
					#credit account
					shares_acc = setup.shares_account.id

					journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.description,'account_id':equity_acc,'move_id':move_id,'debit':line.amount})
					journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.description,'account_id':shares_acc,'move_id':move_id,'credit':line.amount})
					#post member ledger
					member = self.env['sacco.member'].search([('id','=',line.member_id)])
					member_name = member.name
					member_ledger = self.env['sacco.member.ledger.entry']
					member_ledger.create({'member_no':line.member_id,'member_name':line.member_name,'date':today,'transaction_no':self.no,'transaction_name':self.description,'amount':line.amount,'transaction_type':'shares'})

				elif self.transaction_type == 'loan':
					#re-create loans and all loan pre-requisites before posting
					journal_lines = self.env['account.move.line']


					#debit account
					equity_acc = setup.opening_balance_equity.id
					#credit account
					loan_acc = setup.loans_account.id

					journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.description,'account_id':loan_acc,'move_id':move_id,'debit':line.amount})
					journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.description,'account_id':equity_acc,'move_id':move_id,'credit':line.amount})
					#post member ledger
					member = self.env['sacco.member'].search([('id','=',line.member_id)])
					member_name = member.name
					member_ledger = self.env['sacco.member.ledger.entry']
					member_ledger.create({'member_no':line.member_id,'member_name':line.member_name,'date':today,'transaction_no':line.transaction_no,'transaction_name':self.description,'amount':line.loan_approved_amount,'transaction_type':'loan'})
					if line.amount<line.loan_approved_amount:#some repayment for the loan has been done
						principal_paid = line.loan_approved_amount - line.amount
						member_ledger.create({'member_no':line.member_id,'member_name':line.member_name,'date':today,'transaction_no':line.transaction_no,'transaction_name':'Loan Repayment::'+self.description,'amount':-(principal_paid),'transaction_type':'loan'})
					#post loan
					product = self.env['sacco.loan.types'].search([('id','=',line.loan_product_id)])
					loan = self.env['sacco.loan'].create({'name':line.transaction_no,'member_no':line.member_id,'loan_product_type':line.loan_product_id,'installments':product.no_of_installments,'interest':product.interest_rate,'status':'approved','posted':True,'requested_amount':line.loan_approved_amount,
						'approved_amount':line.loan_approved_amount})

		else:
			raise ValidationError("You must validate opening balances before posting!")

class sacco_opening_balances_lines(models.Model):
	_name = 'sacco.opening.balances.lines'

	doc_no = fields.Char()

	transaction_no = fields.Char()
	transaction_id = fields.Char()
	member_id = fields.Char()
	member_no = fields.Char()
	member_name = fields.Char()
	amount = fields.Float()#where transaction type is loans, this will hold the loan balance
	loan_product_code = fields.Char()
	loan_product_id = fields.Char()
	loan_approved_amount = fields.Float()
	processed = fields.Boolean()

