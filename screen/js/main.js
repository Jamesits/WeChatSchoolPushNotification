var api_base_url = "v1/";
var pull_interval = 1000;
var last_connection_status = false;

function getFormattedDate() {
    var date = new Date();
    var str = date.getFullYear() + " 年 " + (date.getMonth() + 1) + " 月 " + date.getDate() + " 日 " +  date.getHours() + ":" + date.getMinutes() + ":" + date.getSeconds();

    return str;
}

function update_display_time() {
    $("#time").text("当前时间：" + getFormattedDate());
}

function update_weather() {
    $.get(api_base_url + "weather", { "location": "杭州" }, function(data, status) {
        $("#weather").text("当前天气：" + data.results[0].now.text + " " + data.results[0].now.temperature + "°C");
    }).fail(function(){
        // 一分钟后重试
        setTimeout(update_weather, 60000);
    })
}

function pull_data(reg_timer){
    var timeStamp = Math.floor(Date.now());
    $.get(api_base_url + "signout_queue", { "timestamp": timeStamp }, function(data, status){
        if (status == "success") {
            if (!last_connection_status) {
                $("#info-reconnected").show(0).delay(2000).hide(0);
                last_connection_status = true;
            }
            $("#alert-no-connection").hide();
            if (data.queue.length) {
                $("#class-list").text(data.queue.map(function(x){return x.class + "(" + x.time + ")"}).join("\n"));
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

    // 启动定时器更新时间
    var updateTimeTimer = setInterval(update_display_time, 500);

    // 启动定时器更新天气
    update_weather();
    var updateWeatherTimer = setInterval(update_weather, 600000);

    // 加载列表
    pull_data(true);
})