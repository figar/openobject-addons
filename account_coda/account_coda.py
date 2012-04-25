# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    
#    Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.
# 
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields
import decimal_precision as dp
import netsvc
from tools.translate import _
logger=netsvc.Logger()

class coda_bank_account(osv.osv):
    _name= 'coda.bank.account'
    _description= 'CODA Bank Account Configuration'

    def _check_currency(self, cr, uid, ids, context=None):
        obj_cba = self.browse(cr, uid, ids[0], context=context)
        if (obj_cba.state == 'normal') and obj_cba.journal:
            if obj_cba.journal.currency and (obj_cba.currency != obj_cba.journal.currency):
                return False
            if not obj_cba.journal.currency and (obj_cba.currency != obj_cba.company_id.currency_id):
                return False
        return True

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'bank_id': fields.many2one('res.partner.bank', 'Bank Account', required=True, 
            help='Bank Account Number.\nThe CODA import function will find its CODA processing parameters on this number.'),
        'description1': fields.char('Primary Account Description', size=35,
            help='The Primary or Secondary Account Description should match the corresponding Account Description in the CODA file.'),
        'description2': fields.char('Secondary Account Description', size=35,
            help='The Primary or Secondary Account Description should match the corresponding Account Description in the CODA file.'),
        'state': fields.selection([
            ('normal', 'Normal'),
            ('info', 'Info')], 
            'Type', required=True, select=1,
            help='No Bank Statements will be generated for CODA Bank Statements from Bank Accounts of type \'Info\'.'),
        'journal': fields.many2one('account.journal', 'Journal', 
            domain=[('type', '=', 'bank')], 
            states={'normal':[('required',True)],'info':[('required',False)]},
            help='Bank Journal for the Bank Statement'),
        'currency': fields.many2one('res.currency', 'Currency', required=True,
            help='The currency of the CODA Bank Statement'),  
        'coda_st_naming': fields.char('Bank Statement Naming Policy', size=64,
            help="Define the rules to create the name of the Bank Statements generated by the CODA processing." \
                 "\nE.g. %(code)s%(y)s/%(paper)s"     
                 "\n\nVariables:" \
                 "\nBank Journal Code: %(code)s" \
                 "\nCurrent Year with Century: %(year)s" \
                 "\nCurrent Year without Century: %(y)s" \
                 "\nCODA sequence number: %(coda)s" \
                 "\nPaper Statement sequence number: %(paper)s"),
        'def_payable': fields.many2one('account.account', 'Default Payable Account', domain=[('type', '=', 'payable')], required=True,
            help= 'Set here the payable account that will be used, by default, if the partner is not found.'),
        'def_receivable': fields.many2one('account.account', 'Default Receivable Account', domain=[('type', '=', 'receivable')], required=True,
            help= 'Set here the receivable account that will be used, by default, if the partner is not found.',),
        'awaiting_account': fields.many2one('account.account', 'Default Account for Unrecognized Movement', domain=[('type', '!=', 'view')], required=True,
            help= 'Set here the default account that will be used if the partner cannot be unambiguously identified.'),
        'transfer_account': fields.many2one('account.account', 'Default Internal Transfer Account', domain=[('code', 'like', '58%'), ('type', '!=', 'view')], required=True,
            help= 'Set here the default account that will be used for internal transfer between own bank accounts (e.g. transfer between current and deposit bank accounts).'),
        'find_bbacom': fields.boolean('Lookup Invoice', required=True, help='Partner lookup via the \'BBA\' Structured Communication field of the Invoice.'),
        'find_partner': fields.boolean('Lookup Partner', required=True, help='Partner lookup via Bank Account Number.'),
        'active': fields.boolean('Active', help='If the active field is set to False, it will allow you to hide the Bank Account without removing it.'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
    }
    _defaults = {
        'currency': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.currency_id.id,
        'state': 'normal',
        'coda_st_naming': '%(code)s/%(y)s/%(coda)s',
        'active': True,   
        'find_bbacom': True,                         
        'find_partner': True,                         
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }
    _sql_constraints = [
        ('account_uniq_1', 'unique (bank_id, description1, currency)', 'The combination of Bank Account, Account Description and Currency must be unique !'),
        ('account_uniq_2', 'unique (bank_id, description2, currency)', 'The combination of Bank Account, Account Description and Currency must be unique !'),
    ]
    _constraints = [
        (_check_currency, '\n\nConfiguration Error! \nThe Bank Account Currency should match the Journal Currency !', ['currency', 'journal']),
    ]
    _order = 'name'

    def name_get(self, cr, uid, ids, context=None):
        res = []
        if not len(ids):
            return res
        for id in self.browse(cr, uid, ids, context=context):
            res.append((id.id, (id.bank_id.iban or id.bank_id.acc_number) + ' (' + id.currency.name + ')' + \
                (id.description1 and (' - ' + id.description1) or '')))
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        cba = self.browse(cr, uid, id, context=context)
        if not default:
            default = {}
        default = default.copy()
        default.update({'journal_id': None})     
        default['description1'] = cba['description1'] or ''
        default['description2'] = cba['description2'] or ''
        default['name'] = (cba['name'] or '') + ' (copy)'
        default['state'] = cba['state']        
        return super(coda_bank_account, self).copy(cr, uid, id, default, context) 

    def onchange_state(self, cr, uid, ids, state):
        return state =='info' and {'value': {'journal': None}} or {}

coda_bank_account()

class account_coda(osv.osv):
    _name = 'account.coda'
    _description = 'Object to store CODA Data Files'
    _order = 'coda_creation_date desc'
    _columns = {
        'name': fields.char('CODA Filename',size=128, readonly=True),
        'coda_data': fields.binary('CODA File', readonly=True),
        'statement_ids': fields.one2many('coda.bank.statement','coda_id','Generated CODA Bank Statements', readonly=True),
        'note': fields.text('Import Log', readonly=True),
        'coda_creation_date': fields.date('CODA Creation Date', readonly=True, select=True),
        'date': fields.date('Import Date', readonly=True, select=True),
        'user_id': fields.many2one('res.users','User', readonly=True, select=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True)
    }
    _defaults = {
        'date': fields.date.context_today,
        'user_id': lambda self,cr,uid,context: uid,
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.coda', context=c),
    }        
    _sql_constraints = [
        ('coda_uniq', 'unique (name, coda_creation_date)', 'This CODA has already been imported !')
    ]  

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context.update({'coda_unlink': True})
        coda_st_obj = self.pool.get('coda.bank.statement')
        bank_st_obj = self.pool.get('account.bank.statement')
        for coda in self.browse(cr, uid, ids, context=context):
            for coda_statement in coda.statement_ids:                 
                if not context.get('coda_statement_unlink', False):
                    if coda_st_obj.exists(cr, uid, coda_statement.id, context=context):
                        coda_st_obj.unlink(cr, uid, [coda_statement.id], context=context)    
                if not context.get('bank_statement_unlink', False):
                    if coda_st_obj.exists(cr, uid, coda_statement.id, context=context) and (coda_statement.type == 'normal') and bank_st_obj.exists(cr, uid, coda_statement.statement_id.id, context=context):
                        bank_st_obj.unlink(cr, uid, [coda_statement.statement_id.id], context=context)                   
        context.update({'coda_unlink': False})
        return super(account_coda, self).unlink(cr, uid, ids, context=context)
  
account_coda()

class account_coda_trans_type(osv.osv):  
    _name = 'account.coda.trans.type'
    _description = 'CODA transaction type'
    _rec_name = 'type' 
    _columns = {
        'type': fields.char('Transaction Type', size=1, required=True),
        'parent_id': fields.many2one('account.coda.trans.type', 'Parent'),
        'description': fields.text('Description', translate=True),
    }
account_coda_trans_type()

class account_coda_trans_code(osv.osv):  
    _name = 'account.coda.trans.code'
    _description = 'CODA transaction code'
    _rec_name = 'code' 
    _columns = {
        'code': fields.char('Code', size=2, required=True, select=1),
        'type': fields.selection([
                ('code', 'Transaction Code'),
                ('family', 'Transaction Family')], 
                'Type', required=True, select=1), 
        'parent_id': fields.many2one('account.coda.trans.code', 'Family', select=1),
        'description': fields.char('Description', size=128, translate=True, select=2),
        'comment': fields.text('Comment', translate=True),
    }
account_coda_trans_code()

class account_coda_trans_category(osv.osv):  
    _name = 'account.coda.trans.category'
    _description = 'CODA transaction category'
    _rec_name = 'category' 
    _columns = {
        'category': fields.char('Transaction Category', size=3, required=True),
        'description': fields.char('Description', size=256, translate=True),
    }
account_coda_trans_category()

class account_coda_comm_type(osv.osv):  
    _name = 'account.coda.comm.type'
    _description = 'CODA structured communication type'
    _rec_name = 'code' 
    _columns = {
        'code': fields.char('Structured Communication Type', size=3, required=True, select=1),
        'description': fields.char('Description', size=128, translate=True),
    }
    _sql_constraints = [
        ('code_uniq', 'unique (code)','The Structured Communication Code must be unique !')
        ]
account_coda_comm_type()

class coda_bank_statement(osv.osv):
    _name = 'coda.bank.statement' 
    _description = 'CODA Bank Statement'    
    
    def _default_journal_id(self, cr, uid, context={}):
        if context.get('journal_id', False):
            return context['journal_id']
        return False

    def _end_balance(self, cursor, user, ids, name, attr, context=None):
        res = {}
        statements = self.browse(cursor, user, ids, context=context)
        for statement in statements:
            res[statement.id] = statement.balance_start
            for line in statement.line_ids:
                    res[statement.id] += line.amount
        for r in res:
            res[r] = round(res[r], 2)
        return res

    def _get_period(self, cr, uid, context={}):
        periods = self.pool.get('account.period').find(cr, uid)
        if periods:
            return periods[0]
        else:
            return False

    _order = 'date desc'
    _columns = {
        'name': fields.char('Name', size=64, required=True, readonly=True),
        'date': fields.date('Date', required=True, readonly=True),
        'coda_id': fields.many2one('account.coda', 'CODA Data File', ondelete='cascade'),
        'type': fields.selection([
            ('normal', 'Normal'),
            ('info', 'Info')], 
            'Type', required=True, readonly=True,
            help='No Bank Statements are associated with CODA Bank Statements of type \'Info\'.'),
        'statement_id': fields.many2one('account.bank.statement', 'Associated Bank Statement'),        
        'journal_id': fields.many2one('account.journal', 'Journal', readonly=True, domain=[('type', '=', 'bank')]),
        'coda_bank_account_id': fields.many2one('coda.bank.account', 'Bank Account', readonly=True),        
        'period_id': fields.many2one('account.period', 'Period', required=True, readonly=True),
        'balance_start': fields.float('Starting Balance', digits_compute=dp.get_precision('Account'), readonly=True),
        'balance_end_real': fields.float('Ending Balance', digits_compute=dp.get_precision('Account'), readonly=True),
        'balance_end': fields.function(_end_balance, method=True, store=True, string='Balance'),        
        'line_ids': fields.one2many('coda.bank.statement.line',
            'statement_id', 'CODA Bank Statement lines', readonly=True),
        'currency': fields.many2one('res.currency', 'Currency', required=True, readonly=True,
            help='The currency of the CODA Bank Statement'),
        'company_id': fields.related('journal_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
    }
    _defaults = {
        'type': 'normal',        
        'currency': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.currency_id.id,
        'journal_id': _default_journal_id,
        'period_id': _get_period,
    }

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None: 
            context = {}
        res = super(coda_bank_statement, self).search(cr, uid, args=args, offset=offset, limit=limit, order=order,
                context=context, count=count)
        if context.get('bank_statement', False) and not res:
            raise osv.except_osv('Warning', _('No CODA Bank Statement found for this Bank Statement!'))
        return res

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context.update({'coda_statement_unlink': True})
        coda_obj = self.pool.get('account.coda')
        bank_st_obj = self.pool.get('account.bank.statement')
        
        # find all CODA bank statements that are associated with the selected CODA bank statements via a common CODA file
        new_ids = []       
        for coda_statement in self.browse(cr, uid, ids, context=context):
            if coda_obj.exists(cr, uid, coda_statement.coda_id.id, context=context):
                new_ids += [x.id for x in coda_obj.browse(cr, uid, coda_statement.coda_id.id, context=context).statement_ids]

        # unlink CODA banks statements as well as associated bank statements and CODA files               
        for coda_statement in self.browse(cr, uid, new_ids, context=context):
            if coda_statement.statement_id.state == 'confirm': 
                raise osv.except_osv(_('Invalid action !'),
                    _("Cannot delete CODA Bank Statement '%s' of Journal '%s'." \
                      "\nThe associated Bank Statement has already been confirmed !" \
                      "\nPlease undo this action first!") \
                      % (coda_statement.name, coda_statement.journal_id.name))
            else:
                if not context.get('coda_unlink', False):
                    if coda_statement.coda_id and coda_obj.exists(cr, uid, coda_statement.coda_id.id, context=context):
                        coda_obj.unlink(cr, uid, [coda_statement.coda_id.id], context=context)
                if not context.get('bank_statement_unlink', False):
                    if coda_statement.statement_id and bank_st_obj.exists(cr, uid, coda_statement.statement_id.id, context=context):
                        bank_st_obj.unlink(cr, uid, [coda_statement.statement_id.id], context=context)    

        context.update({'coda_statement_unlink': False})
        return super(coda_bank_statement, self).unlink(cr, uid, new_ids, context=context)
 
coda_bank_statement()

class account_bank_statement(osv.osv):
    _inherit = 'account.bank.statement'
    _columns = {
        'coda_statement_id': fields.many2one('coda.bank.statement', 'Associated CODA Bank Statement'),
    }
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context.update({'bank_statement_unlink': True})
        coda_obj = self.pool.get('account.coda')
        coda_st_obj = self.pool.get('coda.bank.statement')

        # find all statements that are associated with the selected bank statements via a common CODA file
        ids_plus = []       
        for statement in self.browse(cr, uid, ids, context=context):
            if statement.coda_statement_id:
                for x in coda_obj.browse(cr, uid, statement.coda_statement_id.coda_id.id, context=context).statement_ids:
                    if x.type == 'normal':
                        ids_plus += [x.statement_id.id]
                
        # unlink banks statements as well as associated CODA bank statements and CODA files
        for statement in self.browse(cr, uid, ids_plus, context=context):       
            if not context.get('coda_statement_unlink', False):
                if statement.coda_statement_id and coda_st_obj.exists(cr, uid, statement.coda_statement_id.id, context=context):
                    coda_st_obj.unlink(cr, uid, [statement.coda_statement_id.id], context=context)
            if not context.get('coda_unlink', False):
                if statement.coda_statement_id \
                    and coda_st_obj.exists(cr, uid, statement.coda_statement_id.id, context=context) \
                    and statement.coda_statement_id.coda_id \
                    and coda_obj.exists(cr, uid, statement.coda_statement_id.coda_id.id, context=context):
                        coda_obj.unlink(cr, uid, [statement.coda_statement_id.coda_id.id], context=context)

        context.update({'bank_statement_unlink': False})
        new_ids = list(set(ids + ids_plus))
        return super(account_bank_statement, self).unlink(cr, uid, new_ids, context=context)
         
account_bank_statement()

class coda_bank_statement_line(osv.osv):
    _name = 'coda.bank.statement.line'     
    _order = 'sequence'   
    _description = 'CODA Bank Statement Line'
    _columns = {
        'name': fields.char('Communication', size=268, required=True),
        'sequence': fields.integer('Sequence'),
        'date': fields.date('Entry Date', required=True),
        'val_date': fields.date('Valuta Date'),        
        'account_id': fields.many2one('account.account','Account'),     # remove required=True
        'type': fields.selection([
            ('supplier','Supplier'),
            ('customer','Customer'),
            ('general','General'),
            ('globalisation','Globalisation'),            
            ('information','Information'),    
            ('communication','Free Communication'),          
            ], 'Type', required=True),
        'globalisation_level': fields.integer('Globalisation Level', 
                help="The value which is mentioned (1 to 9), specifies the hierarchy level"
                     " of the globalisation of which this record is the first."
                     "\nThe same code will be repeated at the end of the globalisation."),
        'globalisation_amount': fields.float('Globalisation Amount', digits_compute=dp.get_precision('Account')),      
        'globalisation_id': fields.many2one('account.bank.statement.line.global', 'Globalisation ID', readonly=True,
            help="Code to identify transactions belonging to the same globalisation level within a batch payment"),                                                     
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account')),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'counterparty_name': fields.char('Counterparty Name', size=35),
        'counterparty_bic': fields.char('Counterparty BIC', size=11),                     
        'counterparty_number': fields.char('Counterparty Number', size=34),   
        'counterparty_currency': fields.char('Counterparty Currency', size=3), 
        'statement_id': fields.many2one('coda.bank.statement', 'CODA Bank Statement',
            select=True, required=True, ondelete='cascade'),
        'coda_bank_account_id': fields.related('statement_id', 'coda_bank_account_id', type='many2one', relation='coda.bank.account', string='Bank Account', store=True, readonly=True),
        'ref': fields.char('Reference', size=32),
        'note': fields.text('Notes'),
        'company_id': fields.related('statement_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),        
    }

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if context.get('block_statement_line_delete', False):
            raise osv.except_osv('Warning', _('Delete operation not allowed !'))
        return super(account_bank_statement_line, self).unlink(cr, uid, ids, context=context)

coda_bank_statement_line()       

class account_bank_statement_line_global(osv.osv):
    _inherit = 'account.bank.statement.line.global'
    _columns = {
        'coda_statement_line_ids': fields.one2many('coda.bank.statement.line', 'globalisation_id', 'CODA Bank Statement Lines', readonly=True),
    }
account_bank_statement_line_global()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
