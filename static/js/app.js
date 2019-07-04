$(document).ready(function(){
    // Display the default welcome message on page load
    window.onload = function(){
        $('#welcome').html("<p>Waiting for user...</p>");
    };

    // Connect to the socket server
    var socket = io.connect('https://' + document.domain + ':' + location.port, {secure: true});
    var connect_error_counter = 0;
    // Receive new welcome message from server
    socket.on('newMessage', function(msg) {
        console.log("Welcome message = '" +msg.message+ "'");
        // Update the welcome message to be displayed
        welcome_message = "<p>" + msg.message.toString() + "</p>"
        $('#welcome').html(welcome_message);
        // socket.emit('newMessage');
    });
    socket.emit('newMessage');
    socket.on('connect_error', function(err) {
        // If there are 3 connection errors to the server, close the
        // socket
        console.log('[WARNING] Error connecting to server');
        connect_error_counter++;

        if (connect_error_counter == 3) {
            console.log('[ERROR] Server unreachable, closing socket...');
            socket.disconnect();
            console.log('[DONE] Socket closed');
        }
    });

});
// window.onbeforeunload = function() {
//     websocket.onclose = function () {}; // disable onclose handler first
//     websocket.close();
// };