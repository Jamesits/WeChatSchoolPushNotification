var api_base_url = "v1/";
var pull_interval = 1000;
var last_connection_status = false;

function pull_data(reg_timer){
    $.get(api_base_url + "signout_queue", function(data, status){
        if (status == "success") {
            if (!last_connection_status) {
                $("#info-reconnected").show(0).delay(2000).hide(0);
                last_connection_status = true;
            }
            $("#alert-no-connection").hide();
            if (data.queue.length) {
                $("#class-list").text(data.queue.join("\n"));
            } else {
                $("#class-list").text("（暂无）");
            }
        }
    }).fail(function() {
        $("#alert-no-connection").show();
        $("#info-reconnected").hide();
        last_connection_status = false;
    })
    if (reg_timer == true) {
        setTimeout(pull_data.bind(null, reg_timer), pull_interval);
    }
}

function clear_data(){
    $.post(api_base_url + "clear_signout_queue", null, function(data, status){
        if (status == "success") {
            $('#infoQueueCleared').modal("show");
        } else {

        }
    })
}

$(function(){
    // 注册事件
    $("#btnclear").click(function(){
        $('#questionQueueClear').modal("hide");
        clear_data();
        pull_data();
    });
    $("#btnrefresh").click(function(){
        window.location.reload();
    });
    $("#btnAskClear").click(function(){
        $('#questionQueueClear').modal("show");
    });

    // 加载列表
    pull_data(true);
})