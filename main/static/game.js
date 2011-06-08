var ChatWindow = function(sel) {
    var chat = this;

    chat.print = function(msg, type) {
	type = type | "black";
	var inner = $($(sel).children("div")[0]);
	msg = $("<div />").css("color", type).text(msg);
	inner.append(msg);
	$(sel).scrollTop(inner.height());
    };
};

var GameRoom = function(room_url, username, game_id, hookbox_url) {

  var game_room = this;
  game_room.room_url = room_url;
  game_room.username = username;
  game_room.game_id = game_id;
  game_room.hookbox_url = hookbox_url;

  game_room.turn_type = null;

  game_room.otherteam = null;

  var chatroom = new ChatWindow("#chat");

  function putInChatWindow(msg, type) {
      if( typeof msg == "object" ) {
	  for( var i=0; i<msg.length; ++i ) {
	      chatroom.print(msg[i], type);
	  }
      } else {
	  chatroom.print(msg, type);
      }
  };

  function sendChat(msg) {
      var payload = {msgtype: "chat", msg: msg};
      payload = JSON.stringify(payload);
      window.conn.publish(game_room.game_id, payload);
  }
  game_room.chat = function(form) {
      var msg = $(form).find("input").val();
      $(form).find("input").val("");
      sendChat(msg);
  };

  function infoAbout(unit) {
    var data = {};
    for( var i in unit.data() ) {
      if( i && i != "sprite"
	  && i != "availableMoves"
	  && i != "availableAttacks"
	) {
        data[i] = unit.data(i);
      }
    }
    $("#info").empty();
    $("<div />")
      .css("height", 64)
      .css("width", 64)
      .css("background-image",
	   unit.data("sprite").css("background-image"))
      .appendTo("#info");
    for( var i in data ) {
      $("<div />")
	.html("<b>"+i+"</b>: " + data[i])
	.appendTo("#info");
    }
  }
  $(".sprite").live("hover", function() {
		      infoAbout($(this).data("item"));
		    }, function() {
		      $("info").text("");
		    }
  );

  $(".sprite.availabletarget").live("click", function() {
    $(this).data("item").click();
  });
  $("#board td.available").live("click", function() {
    if( !window.unit ) return;
    if( game_room.turn_type == "move" ) {
      var col = $(this).index();
      var row = $(this).parent("tr").index();
      var fromCol = $(window.unit).parent("td").index();
      var fromRow = $(window.unit).parent("td").parent("tr").index();

      window.unit = null;
      $("#board td.available").removeClass("available");
      $(".ready").removeClass("ready");
      $(".item").removeData("availableMoves");
      $.post(game_room.room_url + "move/",
	{team: window.team,
	 c0: fromCol, c1: col, r0: fromRow, r1: row});
      // TODO: handle error response, and move window.unit = null to success handler
    } else if( game_room.turn_type == "act" ) {
      var target = $(this).find("div.item");
      // error check: target must exist, be an enemy unit
      var c1 = $(this).index();
      var r1 = $(this).parent("tr").index();

      var c0 = $(window.unit).parent("td").index();
      var r0 = $(window.unit).parent("td").parent("tr").index();

      window.unit = null;

      $("#board td.available").removeClass("available");
      $(".ready").removeClass("ready");

      $.post(game_room.room_url + "act/",
	{team: window.team, action: 'attack',
	 c0: c0, r0: r0,
         c1: c1, r1: r1});
      // TODO: handle error response, and move window.unit = null to success handler
    }
  });

  function animateAction(unit, cell, actionType, after) {
    if( actionType != "attack" ) return; // TODO
    var actor = $(unit).data("sprite");
    var target = $(cell).find("div.item").data("sprite");
    actor.addClass("attacking");
    target.addClass("hurting");
    window.setTimeout(function() {
			actor.removeClass("attacking");
			target.removeClass("hurting");
			after && after();
			$.post(game_room.room_url + "ready/");
		      }, 2000);
  };

  function animateTo(unit, cell) {
    var pos = $(cell).offset();
    var img = $(unit).data("sprite");
    img.animate(
      {'top': pos.top, 'left': pos.left},
	2000, function() {
        $.post(game_room.room_url + "ready/");
      });
  };

      $(".sprite.ready").live("click", function() {
        $("table#board td.available").removeClass("available");
        var item = window.unit = $(this).data("item");
	if( game_room.turn_type == "move" ) {
	  var moves = item.data("availableMoves");
	  for( var i=0; i<moves.length; ++i ) {
	    var coor = moves[i];
	    $($($("#board tr")[coor[0]]).children("td")[coor[1]])
	      .addClass("available");
	  }
	  putInChatWindow("Now click on a square to move to; " +
			  "or click on a different unit to move.");
	} else if( game_room.turn_type == "act" ) {
	  var attack = item.data("availableAttacks");
	  for( var i=0; i<attack.length; ++i ) {
	    var coor = attack[i];
	    $($($("#board tr")[coor[0]]).children("td")[coor[1]])
	      .addClass("available")
	      .find("div.item").data("sprite").addClass("availabletarget");
	  }
	  filter = function() {
	    if( $(this).find("div.item").length != 1 ) return false;
	    if( $(this).find("div.item")[0] == item[0] ) return false;
	    if( $(this).find("div.item").data("type") != "unit" ) return false;
	    if( $(this).find("div.item").data("team") == window.team ) return false;
	    return true;
	  };
	  putInChatWindow("Now click on a square to attack; " +
			  "or click on a different unit to act.");
	}
      });

  function hisTurn(team, type) {
      putInChatWindow("It is now " + team + "'s turn to "
		      + type + ".", "black");
      game_room.turn_type = null;
  };
  function myTurn(team, type, availableActions) {
    if( type == "move") {
      var availableMoves = availableActions.move;
      putInChatWindow("It is now your turn! Click on a unit to move it.", "black");
      for( var coords in availableMoves ) {
	var x = eval(coords)[0]; var y = eval(coords)[1];
	tr = $("#board tr")[x];
	td = $(tr).find("td")[y];
	$(td).children("div.item").data("sprite").addClass("ready");
	$(td).children("div.item").data("availableMoves", availableMoves[coords]);
      }
    } else if( type == "act" ) {
      var availableAttacks = availableActions.attack;
      putInChatWindow("It is now your turn! Click on a unit to act.", "black");
      for( var coords in availableAttacks ) {
	var x = eval(coords)[0]; var y = eval(coords)[1];
	tr = $("#board tr")[x];
	td = $(tr).find("td")[y];
	$(td).children("div.item").data("sprite").addClass("ready");
	$(td).children("div.item").data("availableAttacks", availableAttacks[coords]);
      }
    }
    game_room.turn_type = type;
  };

      function get_cookie(cookie_name) {
          var results = document.cookie.match('(^|;) ?' + cookie_name + '=([^;]*)(;|$)');
          if( results ) {
              return unescape(results[2]);
	  }
          return null;
      };

      function reloadBoard(data) {
        $("#board tr").each(function() {
          $(this).removeData();
          $(this).find("div.item").remove();
        });
        $("div.sprite").remove();
        for( coord in data ) {
          var item = data[coord];
          coord = eval(coord.replace("(", "[").replace(")", "]"));
          var tr =
            $("#board tr").slice(coord[0], coord[0]+1)
             .find("td").slice(coord[1], coord[1]+1);
          var el;
          if( tr.find("div.item").length ) {
            el = tr.find("div.item")[0];
            writeEl($(el), item);
          } else {
            el = buildEl(item);
            el.appendTo(tr);
            var sprite = $("<div />").addClass("sprite")
		.attr("data-type", item.type);
	    sprite.appendTo("body");

            if( item.team ) {
              sprite.attr("data-team", item.team);
            }
            if( item.job ) {
              sprite.attr("data-job", item.job);
            }
            el.data("sprite", sprite);
            sprite.data("item", el);
          }
        }
	game_room.repositionSprites();
	game_room.repositionSprites(); // TODO why does it not work until i call it twice?
      };

  game_room.repositionSprites = function() {
      $(".sprite").each(function() {
	      $(this).position({"my": "center", "at": "center", "of": $(this).data("item")});
	  });
  };

      function turnChange(payload) {
        var team = payload.team;
        var board = JSON.parse(payload.board);
        reloadBoard(board);
	var type = payload.turntype;
        if( window.team == team ) {
	    myTurn(team, type, payload.available_actions);
        } else {
          hisTurn(team, type);
        }
      };

      function buildEl(data) {
        var el = $("<div />").addClass("item");
        writeEl(el, data);
        return el;
      };

      function writeEl(el, data) {
        for( attr in data ) {
          el.data(attr, data[attr]);
        }
        return el;
      };

    function connect() {
      document.cookie = "game=" + game_room.game_id;
      document.cookie = "user=" + game_room.username;
      window.conn = hookbox.connect(game_room.hookbox_url);
      window.conn.onSubscribed = function(channelName, subscription) {
        window.subscription = subscription;
        $.ajax({
		 url: game_room.room_url + 'team/' + game_room.username + '/',
		 success: function(data) {
		   window.team = data;
		   game_room.otherteam = data == "blue" ? "red" : "blue";
		 },
		 async: false
	       });
	putInChatWindow("You have joined the game room as the " + window.team + " team.");
        $.post(game_room.room_url + "ready/");

        subscription.onSubscribe = function(frame) {
	  putInChatWindow(frame.user + " has joined the game room as the " + game_room.otherteam + " team.");
        };
	subscription.onUnsubscribe = function(frame) {
	  putInChatWindow(frame.user + " has left the game room.");
	};
        subscription.onPublish = function(frame) {
	    console && console.log(frame);
	  if( frame.channel_name != game_room.game_id ) return;
	    if( typeof frame.payload == "string" ) {
		frame.payload = JSON.parse(frame.payload);
            }
            var msgtype = frame.payload.msgtype;
            if( msgtype == "turnchange" ) {
              turnChange(frame.payload);
	    } else if( msgtype == "chat" ) {
		var type = frame.user == game_room.username ? window.team : game_room.otherteam;
		var msg = "<b>" + frame.user + "</b>: " + frame.payload.msg;
		putInChatWindow(msg, type);
            } else if( msgtype == "move" ) {
              var from = frame.payload.from;
              var to = frame.payload.to;
              var orig = $($("table#board tr")[from.row]).find("td")[from.col];
              var dest = $($("table#board tr")[to.row]).find("td")[to.col];
              var item = $(orig).find("div.item")[0];
              animateTo(item, dest);
            } else if( msgtype == "act" ) {
              var from = frame.payload.from;
              var to = frame.payload.to;
              var orig = $($("table#board tr")[from.row]).find("td")[from.col];
              var dest = $($("table#board tr")[to.row]).find("td")[to.col];
              var item = $(orig).find("div.item")[0];
	      var type = frame.payload.acting_user == game_room.username ? window.team : game_room.otherteam;
	      putInChatWindow(frame.payload.chatBefore, type);
              animateAction(item, dest, frame.payload.action,
			    function() { putInChatWindow(frame.payload.chatAfter, type); });
	    }

        };
      };
      window.conn.subscribe(game_room.game_id);
    };

    game_room.load = function() {
      $.get(game_room.room_url + "json/", function(data) {
        reloadBoard(data);
        connect();
      });
    };
};