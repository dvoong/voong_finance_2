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

$(document).ready(function(){
    get_data();
})