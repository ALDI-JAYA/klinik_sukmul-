from odoo import models, fields, api
import csv
import base64
import logging
from io import StringIO
from datetime import datetime
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class PosOrderImportWizard(models.TransientModel):
    _name = 'pos.order.import.wizard'
    _description = 'Import POS Orders from CSV'

    file = fields.Binary(string='CSV File', required=True)

    def import_orders(self):
        self.ensure_one()
        csv_data = base64.b64decode(self.file).decode('utf-8')
        csv_reader = csv.DictReader(StringIO(csv_data), delimiter=';')

        PosOrder = self.env['pos.order']
        company_id = self.env.company.id  

        pricelist = self.env['product.pricelist'].search([], limit=1)
        if not pricelist:
            raise UserError("Tidak ada pricelist yang tersedia. Pastikan pricelist telah dibuat.")

        session = self.env['pos.session'].search([('state', '=', 'opened')], limit=1)  
        if not session:
            raise UserError("Tidak ada sesi POS yang terbuka. Harap buka sesi POS terlebih dahulu.")

        skipped_rows = []

        for index, row in enumerate(csv_reader, start=1):
            receipt_number = row.get('receipt_number', '').strip()
            if not receipt_number:
                skipped_rows.append(f"Baris {index}: Tidak ada nomor struk.")
                continue  

            partner_id = self._get_partner(row.get('partner'))
            if partner_id is False:
                skipped_rows.append(f"Baris {index}: Partner {row.get('partner')} tidak ditemukan.")
                continue

            product_id = self._get_product(row.get('product_id'))
            if product_id is False:
                skipped_rows.append(f"Baris {index}: Produk {row.get('product_id')} tidak ditemukan.")
                continue

            date_order = self._convert_date(row.get('date_order'))
            quantity = self._convert_float(row.get('quantity'), default=1.0)
            price = self._convert_float(row.get('price'), default=0.0)
            discount = self._convert_float(row.get('discount'), default=0.0)
            tax = self._convert_float(row.get('tax'), default=0.0)
            amount_return = self._convert_float(row.get('amount_return'), default=0.0)
            
            amount_total = (price * quantity) - discount
            amount_tax = amount_total * (tax / 100)

            try:
                order_vals = {
                    'name': receipt_number,
                    'partner_id': partner_id,
                    'date_order': date_order,
                    'amount_total': amount_total,
                    'amount_tax': amount_tax,
                    'amount_return': amount_return,
                    'session_id': session.id,
                    'company_id': company_id,
                    'pricelist_id': pricelist.id,
                    'state': 'paid',
                    'lines': [(0, 0, {
                        'product_id': product_id,
                        'qty': quantity,
                        'price_unit': price,
                        'discount': discount,
                    })]
                }

                PosOrder.create(order_vals)

            except Exception as e:
                skipped_rows.append(f"Baris {index}: Error saat menyimpan order {receipt_number} - {str(e)}")
                continue

        if skipped_rows:
            error_message = "\n".join(skipped_rows)
            _logger.warning(f"Data yang dilewati:\n{error_message}")
            raise UserError(f"{len(skipped_rows)} baris dilewati karena data tidak valid.\n\n{error_message}")

    def _get_partner(self, partner_name):
        Partner = self.env['res.partner'].sudo()
        
        # Jika partner_name kosong, gunakan default "No Name"
        if not partner_name or not isinstance(partner_name, str):
            partner_name = "No Name"

        # Cek apakah partner sudah ada
        partner = Partner.search([('name', 'ilike', partner_name)], limit=1)
        
        if not partner:
            try:
                # Buat partner baru dalam transaksi yang aman
                partner = Partner.create({'name': partner_name})
                self.env.cr.commit()  # Commit transaksi untuk menghindari error database
            except Exception as e:
                self.env.cr.rollback()  # Rollback jika terjadi error
                _logger.error(f"Error creating partner: {e}")
                return False  # Hindari error lebih lanjut

        return partner.id




    def _get_product(self, product_name):
        if not product_name:
            return False
        product = self.env['product.product'].search([('name', 'ilike', product_name)], limit=1)
        return product.id if product else False

    def _convert_date(self, date_str):
        try:
            return datetime.strptime(date_str, '%d/%m/%Y %H:%M') if date_str else fields.Datetime.now()
        except ValueError:
            return fields.Datetime.now()

    def _convert_float(self, value, default=0.0):
        try:
            return float(value) if value else default
        except ValueError:
            return default
