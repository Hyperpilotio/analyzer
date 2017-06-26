$(function () {
    $('.selectpicker-calibration').change(function () {
        var appId = $('.selectpicker-calibration option:selected').val();
        window.location.href = '/singleApp/calibration/' + appId;
    });
    $('.selectpicker-profiling').change(function () {
        var appId = $('.selectpicker-profiling option:selected').val();
        window.location.href = '/singleApp/profiling/' + appId;
    });
});
