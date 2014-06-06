/*
TODO Do something if the user clicks and isn't logged in.
*/
(function() {
   $(document).ready(
     function(){
        $("[data-toggle='tooltip']").tooltip();

        function votedown(e) {
            var parpar = $(e.target).parent().parent();
            var quoteid = parpar.find('.quoteid').html();
            var other = parpar.find('.voteup');
            $.post(
              '/vote/',
              {'quoteid': quoteid, 'vote': 1},
              function() {
                  $(e.target).attr('src', '/images/up.png');
                  $(other).attr('src', '/images/up-clicked.png');
              }
            );

            return false;
          }

      function should_login(e) {
          $('.loginwarning').show(300).fadeOut(4000);
      }

      
      if ($('.loggedin').length) {
         $('.tidbits .voteup').each(
           function() {
               $(this).click(votedown);
           }
         );
      } else {
         $('.tidbits .voteup').each(
           function() {
               $(this).click(should_login);
           }
         );
      
      }

     }
   );
})();
