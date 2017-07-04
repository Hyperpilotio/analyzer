export default () => (
  <div>
    <div className="container">
      <nav className="navbar">
        <div className="nav-left">
          <div className="navbar-item">
            <img className="brand" src="http://placehold.it/40/40" />
          </div>
        </div>
        <div className="nav-center">
          <div className="navbar-item">
            <input type="search" placeholder="Jump to apps, status, services..." />
          </div>
        </div>
        <div className="nav-right nav-sublist">
          <div className="navbar-item">
            <img className="menu-icon" src="http://placehold.it/40/40" />
          </div>
          <div className="navbar-item">
            <img className="user-icon" src="http://placehold.it/40/40" />
          </div>
        </div>
      </nav>
    </div>
    <div className="divider" />
  </div>
)
