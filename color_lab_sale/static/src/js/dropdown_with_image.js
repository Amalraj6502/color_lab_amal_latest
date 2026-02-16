//odoo.define('color_lab_sale.printer_conf_widget', function (require) {
//    "use strict";
//
//    var core = require('web.core');
//    var FieldMany2One = require('web.relational_fields').FieldMany2One;
//    var fieldRegistry = require('web.field_registry');
//
//    var PrinterConfWidget = FieldMany2One.extend({
//        _renderDropdownItem: function (line) {
//            var $item = this._super.apply(this, arguments);
//
//            // Add image to the dropdown item
//            if (line.data.image_printer) {
//                var $image = $('<img>', {
//                    src: 'data:image/png;base64,' + line.data.image_printer,
//                    class: 'printer-conf-image',
//                    width: '24px',
//                    height: '24px',
//                });
//                $item.prepend($image);
//            }
//
//            return $item;
//        },
//    });
//
//    fieldRegistry.add('printer_conf_widget', PrinterConfWidget);
//
//    return {
//        PrinterConfWidget: PrinterConfWidget,
//    };
//
//    <t t-extend="KanbanRecord">
//    <t t-jquery=".o_kanban_card_content" t-operation="append">
//        <script>
//            function onCardClick(record) {
//                var saleOrderId = record.data.sale_order_id.res_id;
//                if (saleOrderId) {
//                    this.do_action({
//                        type: 'ir.actions.act_window',
//                        res_model: 'sale.order',
//                        res_id: saleOrderId,
//                        views: [[false, 'form']],
//                        target: 'current',
//                    });
//                }
//            }
//        </script>
//    </t>
//</t>
//});