$(function(){

  // ---- starfield ----
  var starCount = 90;
  var $stars = $('#stars');
  for(var i=0;i<starCount;i++){
    var size = Math.random()*2.2+0.6;
    var $s = $('<span>').css({
      width: size+'px', height:size+'px',
      top: Math.random()*100+'%', left: Math.random()*100+'%',
      animationDelay: (Math.random()*4)+'s'
    });
    $stars.append($s);
  }

  // ---- mobile nav toggle ----
  $('#menuToggle').on('click', function(){
    $('#navLinks').toggleClass('open');
  });
  $('.nav-links a').on('click', function(){
    $('#navLinks').removeClass('open');
  });

  // ---- animated stat counters ----
  function animateCount($el){
    var target = parseInt($el.attr('data-count'), 10);
    var $val = $el.find('.val');
    $({n:0}).animate({n:target}, {
      duration: 1200,
      easing: 'swing',
      step: function(now){ $val.text(Math.floor(now)); },
      complete: function(){ $val.text(target); }
    });
  }
  var counted = false;
  function checkStats(){
    if(counted) return;
    var top = $('.hero-right').offset().top;
    if($(window).scrollTop() + $(window).height() > top + 40){
      counted = true;
      $('.num').each(function(){ animateCount($(this)); });
    }
  }
  $(window).on('scroll', checkStats);
  checkStats();

  // ---- speakers data ----
  var speakers = [
    {name:"Sam Olawale Sholademi", role:"Chairman", format: 'jpeg'},
    {name:"Maduka Sopulu", role:"MD/CEO", format: 'png'},
    {name:"Uchechukwu Lynda", role:"HR Manager", format: 'jpeg'},
    {name:"Paul Ugwu", role:"ERP specialist | Snr Software Engineer", format: 'jpeg'},
    {name:"Kosisochukwu", role:"UI/UX", format: 'png'},
    {name:"Juliana", role:"Senior Accountant", format: 'jpeg'},
    {name:"Uchenna Anumba", role:"Head Business Intelligence", format: 'jpeg'},
    {name:"Olawale Babalola", role:"Technical Consultant", format: 'png'},
    {name:"Emeka Okoli", role:"Software Manager", format: 'png'},
    {name:"Joy Ezeurike", role:"Head Legal", format: 'png'},
    {name:"Micheal Ndunwa", role:"Software Developer", format: 'jpeg'},
    {name:"Kadiri Emmanuel", role:"Software Developer", format: 'png'}
  ];
  var $grid = $('#speakerGrid');
  speakers.forEach(function(sp){
    var $card = $('<div>').addClass('speaker-card');
    $card.append(
      $('<div>').addClass('speaker-photo').append(
        $('<img>').attr({src:`/website_africa/static/src/img/${sp.name}.${sp.format}`, alt: ''})
      )
    );
    $card.append($('<h3>').text(sp.name));
    $card.append($('<p>').text(sp.role));
    $grid.append($card);
  });

  // reveal speaker cards on scroll
  function revealSpeakers(){
    $('.speaker-card').each(function(){
      var top = $(this).offset().top;
      if($(window).scrollTop() + $(window).height() > top + 60){
        $(this).addClass('in-view');
      }
    });
  }
  $(window).on('scroll', revealSpeakers);
  revealSpeakers();

  // ---- app icons ----
  var apps = [
    {name:"Accounting", color:"#e0a13a", ic:"%"},
    {name:"Website", color:"#3ea0cf", ic:"🌐"},
    {name:"Inventory", color:"#c8632f", ic:"📦"},
    {name:"HR", color:"#9b6bd6", ic:"👥"},
    {name:"MRP", color:"#e0a13a", ic:"🏭"},
    {name:"eCommerce", color:"#c23e6b", ic:"🛍️"},
    {name:"CRM", color:"#3ecf8e", ic:"📈"},
    {name:"Sales", color:"#e05a3e", ic:"💹"}
  ];
  var $appsGrid = $('#appsGrid');
  apps.forEach(function(a){
    var $tile = $('<div>').addClass('app-tile');
    $tile.append($('<div>').addClass('ic').css('background', a.color+'33').text(a.ic));
    $tile.append($('<span>').text(a.name));
    $appsGrid.append($tile);
  });
  $appsGrid.append($('<div>').addClass('and-more').html('↖ And many more!'));

});