
let simulation;
let svg, g;
let zoom;
let activeNode = null;

document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById("d3-container");
    const apiUrlBase = container.getAttribute("data-api-url");
    const depthControl = document.getElementById("depthControl");
    const depthLabel = document.getElementById("depthLabel");
    
    // Init SVG
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    svg = d3.select("#d3-container")
        .append("svg")
        .attr("width", "100%")
        .attr("height", "100%")
        .attr("viewBox", [0, 0, width, height]);
        
    g = svg.append("g");
    
    zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => g.attr("transform", event.transform));
        
    svg.call(zoom);
    
    // Resize handler
    window.addEventListener('resize', () => {
        svg.attr("viewBox", [0, 0, container.clientWidth, container.clientHeight]);
        if(simulation) {
            simulation.force("center", d3.forceCenter(container.clientWidth / 2, container.clientHeight / 2));
            simulation.alpha(0.3).restart();
        }
    });

    function loadGraph(depth) {
        depthLabel.textContent = depth;
        
        fetch(`${apiUrlBase}?depth=${depth}`)
            .then(res => res.json())
            .then(data => {
                // Update stats
                const totalEl = document.getElementById('stat-total');
                if (totalEl) totalEl.textContent = data.stats.total_collaborators || data.stats.total_collaborations || 0;
                
                const estEl = document.getElementById('stat-est');
                if (estEl) estEl.textContent = data.stats.established || 0;
                
                const ongEl = document.getElementById('stat-ong');
                if (ongEl) ongEl.textContent = data.stats.ongoing || 0;
                
                const vertEl = document.getElementById('stat-vertices');
                if (vertEl) vertEl.textContent = data.stats.total_researchers || data.nodes.length || 0;
                
                renderGraph(data.nodes, data.links, width, height);
            })
            .catch(err => console.error("Error loading graph:", err));
    }
    
    // Initial load
    loadGraph(1);
    
    // Depth slider listener
    depthControl.addEventListener("change", (e) => {
        loadGraph(e.target.value);
    });
});


function renderGraph(nodes, links, width, height) {
    // Clear previous
    g.selectAll("*").remove();
    
    // Colors for borders
    const colorRoot = "#ec4899"; // Pink for the center person
    const colorDirect = "#10b981"; // Emerald for direct
    const colorIndirect = "#6366f1"; // Indigo for extended network
    
    // Calculate node distance from root for coloring
    const rootNode = nodes.find(n => n.is_root);
    
    // Initialize simulation
    simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.id).distance(120).strength(1))
        .force("charge", d3.forceManyBody().strength(-800))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collide", d3.forceCollide().radius(d => d.is_root ? 60 : 45).iterations(2));

    // Glow filter definitions
    const defs = svg.append("defs");
    
    // Glow filter
    const filter = defs.append("filter")
        .attr("id", "glow")
        .attr("x", "-20%")
        .attr("y", "-20%")
        .attr("width", "140%")
        .attr("height", "140%");
    filter.append("feGaussianBlur")
        .attr("stdDeviation", "3")
        .attr("result", "blur");
    filter.append("feComposite")
        .attr("in", "SourceGraphic")
        .attr("in2", "blur")
        .attr("operator", "over");

    // Clip paths for images
    nodes.forEach(d => {
        defs.append("clipPath")
            .attr("id", "clip-" + d.id)
            .append("circle")
            .attr("r", d.is_root ? 30 : 20);
    });

    // Links
    const link = g.append("g")
        .selectAll("line")
        .data(links)
        .enter().append("line")
        .attr("class", d => d.status === "ONGOING" ? "link-ongoing" : "link-established");

    // Nodes
    const node = g.append("g")
        .selectAll("g")
        .data(nodes)
        .enter().append("g")
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    // Avatar background circle (for border)
    node.append("circle")
        .attr("class", "node-circle")
        .attr("r", d => d.is_root ? 34 : 23)
        .attr("fill", "transparent")
        .attr("stroke", d => {
            if(d.is_root) return colorRoot;
            const isDirect = rootNode && links.some(l => {
                const s = typeof l.source === 'object' ? l.source.id : l.source;
                const t = typeof l.target === 'object' ? l.target.id : l.target;
                return (s === rootNode.id && t === d.id) || (t === rootNode.id && s === d.id);
            });
            return isDirect ? colorDirect : colorIndirect;
        })
        .attr("stroke-width", d => d.is_root ? 4 : 3)
        .attr("filter", "url(#glow)")
        .on("click", (event, d) => showNodeInfo(event, d));

    // Avatar Image
    node.append("image")
        .attr("xlink:href", d => d.avatar)
        .attr("x", d => d.is_root ? -30 : -20)
        .attr("y", d => d.is_root ? -30 : -20)
        .attr("height", d => d.is_root ? 60 : 40)
        .attr("width", d => d.is_root ? 60 : 40)
        .attr("clip-path", d => "url(#clip-" + d.id + ")")
        .style("cursor", "pointer")
        .on("click", (event, d) => showNodeInfo(event, d));

    // Labels with nice background for readability
    const labelGroup = node.append("g")
        .attr("transform", d => `translate(0, ${d.is_root ? 45 : 33})`);
        
    labelGroup.append("rect")
        .attr("fill", "rgba(0, 0, 0, 0.7)")
        .attr("rx", 10)
        .attr("ry", 10)
        .attr("x", d => -(d.name.length * 4) - 8)
        .attr("y", -12)
        .attr("width", d => (d.name.length * 8) + 16)
        .attr("height", 20);

    labelGroup.append("text")
        .attr("class", "node-label")
        .attr("text-anchor", "middle")
        .attr("dy", 2)
        .text(d => d.name);

    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node.attr("transform", d => `translate(${d.x},${d.y})`);
    });
    
    // SVG click hides info
    svg.on("click", (event) => {
        if(event.target.tagName === 'svg') {
            closeNodeInfo();
        }
    });

    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}
function showNodeInfo(event, d) {
    event.stopPropagation();
    const card = document.getElementById('node-info-card');
    document.getElementById('node-name').textContent = d.name;
    document.getElementById('node-affil').textContent = d.affiliation || "No affiliation listed";
    
    // Set links for profile and network
    const profileBtn = document.getElementById('node-profile-link');
    const networkBtn = document.getElementById('node-network-link');
    
    profileBtn.href = `/profile/${d.slug}`;
    networkBtn.href = `/r/${d.slug}`;
    
    if(d.is_root) {
        networkBtn.classList.add('d-none');
    } else {
        networkBtn.classList.remove('d-none');
    }
    
    card.classList.remove('d-none');
    
    // Position card near mouse but inside bounds
    const container = document.getElementById("d3-container").getBoundingClientRect();
    let x = event.clientX - container.left + 20;
    let y = event.clientY - container.top - 20;
    
    if (x + 220 > container.width) x = event.clientX - container.left - 240;
    
    card.style.left = `${x}px`;
    card.style.top = `${y}px`;
}

function closeNodeInfo() {
    document.getElementById('node-info-card').classList.add('d-none');
}
