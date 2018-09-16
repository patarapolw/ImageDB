const tagsBar = document.getElementById('tags-bar');
const inputBar = document.getElementById('input-bar');
const imageCanvas = document.getElementById('image-canvas');

let tags = [];
let imagePath = '';

inputBar.value = imagePath;

inputBar.onpaste = ()=>{
  const items = (event.clipboardData || event.originalEvent.clipboardData).items;
  // console.log(items); // will give you the mime types
  for (index in items) {
    const item = items[index];
    if (item.kind === 'file') {
      const file = item.getAsFile();
      console.log(file);
      let reader = new FileReader();
      reader.onload = function(event) {
        const extension = file.type.match(/\/([a-z0-9]+)/i)[1].toLowerCase();

        let formData = new FormData();
        formData.append('file', file, file.name);
        formData.append('extension', extension);
        formData.append('mimetype', file.type);
        formData.append('submission-type', 'paste');
        // formData.append('imagePath', imagePath);
        formData.append('tags', tags);
        fetch('/api/images/create', {
          method: 'POST',
          body: formData
        }).then(response=>response.json())
          .then(responseJson=>{
            inputBar.value = responseJson.filename;
            imageCanvas.src = '/images?filename=' + encodeURIComponent(responseJson.trueFilename);
          });
      };
      reader.readAsBinaryString(file);
    }
  }
}

inputBar.addEventListener("keydown", function(event) {
  imagePath = inputBar.value;
});

inputBar.addEventListener("keyup", function(event) {
  if (event.keyCode === 13) {
    fetch('/api/images/rename', {
      method: 'POST',
      headers: {
        "Content-Type": "application/json; charset=utf-8",
      },
      body: JSON.stringify({
        'filename': imagePath,
        'tags': tags
      })
    }).then(response=>response.json())
      .then(responseJson=>{
        inputBar.value = responseJson.filename;
        imageCanvas.src = '/images?filename=' + encodeURIComponent(responseJson.trueFilename);

        alert('Renaming successful!');
      });
  }
});

tagsBar.addEventListener("keydown", function(event) {
  function purge(tag){
    tag = tag.trim();
    if(tag){
      tags.push(tag);
    }
  }

  tags = [];
  let purgable = true;
  let currentTag = ''

  tagsBar.value.split('').forEach((character, index)=>{
    if(character === ',' && purgable){
      if(purgable){
        purge(currentTag);
        currentTag = '';
      } else {
        currentTag += character;
      }
    } else if (character === '\"'){
      purgable = !purgable;
    } else {
      currentTag += character;
    }
  });

  purge(currentTag);
})
