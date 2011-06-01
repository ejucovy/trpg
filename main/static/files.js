function buildUrl(text) {
  return "/images/" + text;
};

var images = {
  rock: "rock.jpg",
  knight: "knight.png",
  winger: "winger.png",
  healer: "healer.png",
  bear: "bear.png",
  smallrus: "smallrus.png",
};

function getUrl(data) {
  if( data.type == "rock" )
    return buildUrl(images[data.type]);
  return buildUrl(data.team + "/" + images[data.job]);
};
