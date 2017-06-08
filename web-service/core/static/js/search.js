$(function () {
    $('.selectpicker-calibration').change(function () {
        var request_data = $('.selectpicker-calibration option:selected').val();
        window.location.href = '/single_app/calibration/' + request_data;
    });
    $('.selectpicker-profiling').change(function () {
        var request_data = $('.selectpicker-profiling option:selected').val();
        window.location.href = '/single_app/profiling/' + request_data;
    });
});
