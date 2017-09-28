console.log('home');

function get_data(args){
    $.get('/get-data', args)
        .done(function(data, status, xhr){
        console.log('done');
        console.log(data);

        var selection = d3.select('#balance-table tbody')
        .selectAll('tr.table-entry')
        .data(data, function(d){return d.date});

        console.log(selection);

        selection.enter()
            .append('tr')
            .attr('class', 'table-entry')
            .html(function(d){
            return '<td>' + d.date.slice(0, 10) + '</td><td>£' + d.balance + '</td>';
        })

    }).fail(function(xhr, status, status_text){
        var x = d3.select('#errors')
        .append('div')
        .attr('class', 'alert alert-danger')
        .html('Failed to get data, statusText: ' + status_text + '. Check console for full error.')

        console.log(xhr);
        console.log(status);
        console.log(status_text);

    })
}

$('#new-transaction-form').submit(function(e){
    console.log('new_transaction');

    e.preventDefault();
    console.log('submit-form');
    console.log($(this).serialize());
    
    var form = this;

    $.post('/create-transaction', $(this).serialize())
        .done(function(data, status, xhr){

        console.log('create-transaction done');
        console.log(data);

        var data = d3.select('#balance-table tbody')
        .selectAll('tr.table-entry')
        .data();

        console.log('data');
        console.log(data);

        var date_range = [moment.utc(data[0].date), moment.utc(data[data.length - 1].date)];
        console.log('date_range');
        console.log(date_range);

        var transaction_date = moment.utc($(form).find('input#date-input').val());
        console.log('transaction_date');
        console.log(transaction_date);

        if(transaction_date > date_range[1]){
            // do nothing, don't need to update balance
            console.log('transation_date > date_range[1]')
        } else {
            var start = d3.max([transaction_date, date_range[0]]);
            var end = date_range[1];
            $.get('/get-balance', {start: start.format('YYYY-MM-DD'), end: end.format('YYYY-MM-DD')})
                .done(function(data, status, xhr){
                console.log('get-balance done: ');
                console.log(data);
            });
        }
    });

})

$(document).ready(function(){
    get_data();
})