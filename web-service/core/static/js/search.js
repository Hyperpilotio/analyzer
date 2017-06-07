$(function () {
    $('.selectpicker').change(function () {
        var request_data = $('.selectpicker option:selected').text();
        window.location.href = '/single_app/show/' + request_data;
    });
});
