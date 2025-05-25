odoo.define('klinik_sukmul.body_chart_drawing', function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');
    var ajax = require('web.ajax');

    var BodyChartDrawing = Widget.extend({
        template: 'body_chart_drawing_template',

        events: {
            'click #drawButton': 'onDrawClick',  // Event handler untuk tombol Draw
        },

        onDrawClick: function (event) {
            event.preventDefault();  // Mencegah reload halaman

            // Mengaktifkan kemampuan menggambar
            this.enableDrawing();
        },

        enableDrawing: function () {
            var canvas = document.getElementById('drawCanvas');
            var ctx = canvas.getContext('2d');
            var isDrawing = false;

            // Menangani perubahan kursor
            document.body.style.cursor = 'crosshair';  // Mengubah kursor menjadi crosshair (pensil)

            // Mengatur event mouse untuk menggambar
            canvas.addEventListener('mousedown', function (e) {
                isDrawing = true;
                ctx.beginPath();
                ctx.moveTo(e.offsetX, e.offsetY);
            });

            canvas.addEventListener('mousemove', function (e) {
                if (isDrawing) {
                    ctx.lineTo(e.offsetX, e.offsetY);
                    ctx.stroke();
                }
            });

            canvas.addEventListener('mouseup', function () {
                isDrawing = false;
            });

            canvas.addEventListener('mouseout', function () {
                isDrawing = false;
            });
        },

        start: function () {
            var canvas = document.getElementById('drawCanvas');
            var img = document.getElementById('bodyImage');
            canvas.width = img.width;
            canvas.height = img.height;
            this._super.apply(this, arguments);
        }
    });

    core.action_registry.add('klinik_sukmul.body_chart_drawing', BodyChartDrawing);

    return BodyChartDrawing;
});
